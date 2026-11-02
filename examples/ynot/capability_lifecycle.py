"""Acquire a tested capability, reuse it in a new process, then revoke it.

Default: deterministic lifecycle control. --live: paired independent model runs;
the direct baseline can test, save and reuse code too. Neither arm sees holdouts.
"""

import argparse
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path
from uuid import uuid4

from jsonschema import Draft202012Validator

from examples.ynot.schema_case import CONTROL_SOURCE, SPECIFICATION, contract, later_jobs
from ynot import CapabilityStore, ExecutionAllowance, PyodideExecutor
from ynot.capabilities import CapabilityError

SCOPE = "orchestra-development-example"


def canonical(value):
    return json.dumps(value, sort_keys=True, allow_nan=False)


def initial_observation():
    schema = {"type": "string", "nullable": True, "description": "Optional display name"}
    errors = list(Draft202012Validator(schema).iter_errors(None))
    return {"schema": schema, "payload": None, "validator_error": errors[0].message}


def direct_check(source, executor, allowance):
    """Competent baseline: the same host checks, without YNOT's saved artefact."""
    cases = []
    for index, case in enumerate(contract().cases):
        allowance.consume()
        try:
            output = executor(source, case.payload)
        except Exception as exc:
            passed, reason = False, f"executor_error:{type(exc).__name__}"
        else:
            try:
                output_json = canonical(output)
                Draft202012Validator(contract().output_schema).validate(output)
            except Exception:
                passed, reason = False, "invalid_output"
            else:
                passed = output_json == canonical(case.expected)
                reason = "matched" if passed else "unexpected_output"
        cases.append({"index": index, "passed": passed, "reason": reason})
    return {"passed": all(case["passed"] for case in cases), "cases": cases}


def reuse(folder, arm, capability_id, *, revoked=False):
    executor = PyodideExecutor()
    allowance = ExecutionAllowance(4)
    store = CapabilityStore(folder / "store", SCOPE, executor.policy)
    if revoked:
        try:
            store.run(capability_id, {}, contract(), executor, allowance)
        except CapabilityError:
            return {"revocation_blocked": True, "executions": allowance.used}
        raise RuntimeError("Revoked capability remained executable")
    results = []
    failures = []
    for case in later_jobs():
        try:
            if arm == "ynot":
                output = store.run(capability_id, case.payload, contract(), executor, allowance)
            else:
                allowance.consume()
                output = executor((folder / "candidate.py").read_text(), case.payload)
            results.append(canonical(output) == canonical(case.expected))
            failures.append(None if results[-1] else "unexpected_output")
        except Exception as exc:
            results.append(False)
            failures.append(type(exc).__name__)
    return {
        "heldout_passes": sum(results),
        "heldout_cases": len(results),
        "executions": allowance.used,
        "model_calls": 0,
        "failures": failures,
    }


def fresh_reuse(folder, arm, capability_id, *, revoked=False):
    command = [
        sys.executable,
        "-m",
        __name__ if __name__ != "__main__" else "examples.ynot.capability_lifecycle",
        "--reuse",
        arm,
        "--store",
        str(folder),
        "--capability-id",
        capability_id or "",
    ]
    if revoked:
        command.append("--revoked")
    try:
        completed = subprocess.run(command, text=True, capture_output=True, check=True, timeout=180)
        return json.loads(completed.stdout)
    except (subprocess.SubprocessError, ValueError) as exc:
        # A dead subprocess cannot attest its executed-case count. Retain that
        # uncertainty instead of dropping the failed arm from the comparison.
        return {"error": type(exc).__name__, "executions": None, "model_calls": 0}


def run_arm(folder, arm, *, live, model, reasoning):
    folder.mkdir(parents=True)
    started = time.monotonic()
    executor = PyodideExecutor()
    allowance = ExecutionAllowance(28)
    store = CapabilityStore(folder / "store", SCOPE, executor.policy)
    attempts = []
    host = None
    if live:
        from examples.ynot.live_codex import CodexHost

        host = CodexHost(
            folder / "model",
            max_invocations=3,
            timeout=150,
            mission_seconds=600,
            model=model,
            reasoning_effort=reasoning,
        )
    prompt = (
        "Repair this API schema compatibility failure and leave reusable Python code for later schemas.\n"
        "Observed from the actual JSON Schema validator:\n"
        + canonical(initial_observation())
        + "\nRequired behaviour:\n"
        + SPECIFICATION
        + "\nYou have up to three candidate attempts. Host acceptance cases and later inputs are withheld."
        + "\nReturn a JSON object with exactly one field, source, containing standalone Python defining transform(payload)."
    )
    candidate_id = None
    source = None
    accepted = False
    for attempt in range(3 if live else 2):
        source = None
        try:
            if live:
                response, _ = host.invoke(
                    prompt,
                    schema={
                        "type": "object",
                        "properties": {"source": {"type": "string"}},
                        "required": ["source"],
                        "additionalProperties": False,
                    },
                )
                source = json.loads(response)["source"]
                if not isinstance(source, str):
                    raise ValueError("Candidate source must be text")
            else:
                source = "def transform(payload):\n    return payload\n" if attempt == 0 else CONTROL_SOURCE
            if arm == "ynot":
                result = store.qualify(source, contract(), executor, allowance)
                feedback = {"passed": result.promoted, "cases": [case.model_dump() for case in result.receipt.cases]}
                candidate_id = result.capability_id
                (folder / f"qualification-{attempt + 1}.json").write_text(result.model_dump_json(indent=2))
            else:
                feedback = direct_check(source, executor, allowance)
        except Exception as exc:
            if not isinstance(source, str):
                source = None
            feedback = {"passed": False, "cases": [], "error": type(exc).__name__}
        attempts.append(feedback)
        if isinstance(source, str):
            (folder / f"candidate-{attempt + 1}.py").write_text(source)
        if feedback["passed"]:
            accepted = True
            (folder / "candidate.py").write_text(source)
            break
        prompt += (
            "\nPrevious candidate:\n" + (source or "No valid candidate") + "\nHost feedback:\n" + canonical(feedback)
        )
    qualification_seconds = time.monotonic() - started
    reused = fresh_reuse(folder, arm, candidate_id) if accepted else None
    elapsed = time.monotonic() - started
    record = {
        "arm": arm,
        "mode": "live" if live else "scripted_control",
        "attempts": len(attempts),
        "accepted": accepted,
        "attempt_feedback": attempts,
        "qualification_passes": sum(case["passed"] for case in attempts[-1]["cases"]),
        "qualification_cases": len(contract().cases),
        "qualification_executions": allowance.used,
        "source_sha256": hashlib.sha256(source.encode()).hexdigest() if isinstance(source, str) else None,
        "contract_sha256": contract().digest,
        "qualification_seconds": round(qualification_seconds, 3),
        "total_seconds": round(elapsed, 3),
        "reuse": reused,
        "model_calls": len(host.calls) if host else 0,
        "usage": [usage for call in host.calls for usage in call.get("usage", [])] if host else [],
        "capability_id": candidate_id,
        "executor_policy": executor.policy,
    }
    if arm == "ynot" and accepted:
        store.revoke(candidate_id, "Reference lifecycle revocation control after successful reuse")
        record["revocation_control"] = fresh_reuse(folder, arm, candidate_id, revoked=True)
    (folder / "result.json").write_text(json.dumps(record, indent=2) + "\n")
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--store", type=Path, required=True)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--model", default="gpt-6-astra")
    parser.add_argument("--reasoning", default="medium")
    parser.add_argument("--order", choices=("direct-first", "ynot-first"), default="direct-first")
    parser.add_argument("--reuse", choices=("direct", "ynot"), help=argparse.SUPPRESS)
    parser.add_argument("--capability-id", default="", help=argparse.SUPPRESS)
    parser.add_argument("--revoked", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.reuse:
        print(json.dumps(reuse(args.store, args.reuse, args.capability_id, revoked=args.revoked)))
        return
    # Every invocation has a fresh store; repeated demos cannot revive a revoked ID.
    folder = args.store.resolve() / uuid4().hex[:12]
    arms = ("direct", "ynot") if args.order == "direct-first" else ("ynot", "direct")
    if not args.live:
        arms = ("ynot",)
    result = {
        "mode": "live_pair" if args.live else "scripted_control",
        "model": args.model if args.live else None,
        "reasoning": args.reasoning if args.live else None,
        "order": list(arms),
        "results": [],
    }
    for arm in arms:
        try:
            arm_result = run_arm(folder / arm, arm, live=args.live, model=args.model, reasoning=args.reasoning)
        except Exception as exc:
            # Preserve an infrastructure failure and still run the independent arm.
            arm_result = {
                "arm": arm,
                "accepted": False,
                "error": type(exc).__name__,
                "accounting": "incomplete; inspect saved arm traces",
            }
        result["results"].append(arm_result)
        (folder / "comparison.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"evidence": str(folder), **result}, indent=2))
    if any(not arm.get("accepted") or arm.get("reuse", {}).get("heldout_passes") != 4 for arm in result["results"]):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
