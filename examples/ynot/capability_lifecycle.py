"""Acquire a tested capability, reuse it in a new process, then revoke it.

Default: deterministic lifecycle control. --live: paired independent model runs;
the direct and DSPy baselines can test, save and reuse code too. Neither arm
sees holdouts. --case selects the development job. Every invocation creates a
fresh store directory, so a revoked identity cannot be revived by a repeat run.
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

from examples.ynot import schema_case, strict_schema_case
from ynot import CapabilityStore, ExecutionAllowance, PyodideExecutor
from ynot.capabilities import CapabilityError

SCOPE = "orchestra-development-example"
CASES = {module.NAME: module for module in (schema_case, strict_schema_case)}
ARMS = ("direct", "dspy", "ynot")


def canonical(value):
    return json.dumps(value, sort_keys=True, allow_nan=False)


def direct_check(source, executor, allowance, case=schema_case):
    """Competent baseline: the same host checks, without YNOT's saved artefact."""
    contract = case.contract()
    cases = []
    for index, acceptance in enumerate(contract.cases):
        allowance.consume()
        try:
            output = executor(source, acceptance.payload)
        except Exception as exc:
            passed, reason = False, f"executor_error:{type(exc).__name__}"
        else:
            try:
                output_json = canonical(output)
                Draft202012Validator(contract.output_schema).validate(output)
            except Exception:
                passed, reason = False, "invalid_output"
            else:
                passed = output_json == canonical(acceptance.expected)
                reason = "matched" if passed else "unexpected_output"
        cases.append({"index": index, "passed": passed, "reason": reason})
    return {"passed": all(case["passed"] for case in cases), "cases": cases}


def reuse(folder, arm, capability_id, *, revoked=False, case=schema_case):
    executor = PyodideExecutor()
    holdouts = case.later_jobs()
    allowance = ExecutionAllowance(len(holdouts))
    store = CapabilityStore(folder / "store", SCOPE, executor.policy)
    if revoked:
        try:
            store.run(capability_id, {}, case.contract(), executor, allowance)
        except CapabilityError:
            return {"revocation_blocked": True, "executions": allowance.used}
        raise RuntimeError("Revoked capability remained executable")
    results = []
    failures = []
    for acceptance in holdouts:
        try:
            if arm == "ynot":
                output = store.run(capability_id, acceptance.payload, case.contract(), executor, allowance)
            else:
                allowance.consume()
                output = executor((folder / "candidate.py").read_text(), acceptance.payload)
            results.append(canonical(output) == canonical(acceptance.expected))
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


def fresh_reuse(folder, arm, capability_id, *, revoked=False, case=schema_case):
    command = [
        sys.executable,
        "-m",
        __name__ if __name__ != "__main__" else "examples.ynot.capability_lifecycle",
        "--reuse",
        arm,
        "--case",
        case.NAME,
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


def build_dspy_program(host):
    """Current DSPy: a plain predictor on the same Codex engine, with no optimiser run."""
    import dspy
    from examples.ynot.live_codex import CodexEngine

    class WriteCapability(dspy.Signature):
        """Write standalone Python defining transform(payload) that satisfies the task."""

        task: str = dspy.InputField()
        feedback: str = dspy.InputField(desc="Previous candidates and host feedback, or none")
        source: str = dspy.OutputField(desc="Standalone Python source defining transform(payload)")

    program = dspy.Predict(WriteCapability)
    program.set_lm(dspy.BaseLM("custom/codex-cli-default", engine=CodexEngine(host), cache=False, num_retries=0))

    def generate(task, feedback):
        with dspy.context(adapter=dspy.ChatAdapter()):
            return program(task=task, feedback=feedback).source

    def save(path):
        # The CLI engine holds a live process boundary, not serialisable state; save the programme without it.
        lm, program.lm = program.lm, None
        try:
            program.save(path)
        finally:
            program.lm = lm

    generate.save = save
    return generate


def candidate_prompt(case):
    return (
        case.TASK
        + "\nObserved failure:\n"
        + canonical(case.initial_observation())
        + "\nRequired behaviour:\n"
        + case.SPECIFICATION
        + "\nYou have up to three candidate attempts. Host acceptance cases and later inputs are withheld."
    )


def run_arm(folder, arm, *, live, model, reasoning, case=schema_case):
    if arm not in ARMS:
        raise ValueError(f"Unknown arm {arm!r}")
    if arm == "dspy" and not live:
        raise ValueError("The DSPy arm is a live baseline; the scripted control exercises the lifecycle only")
    folder.mkdir(parents=True)
    started = time.monotonic()
    executor = PyodideExecutor()
    allowance = ExecutionAllowance(28)
    store = CapabilityStore(folder / "store", SCOPE, executor.policy)
    contract = case.contract()
    attempts = []
    host = None
    program = None
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
        if arm == "dspy":
            program = build_dspy_program(host)
    task = candidate_prompt(case)
    prompt = (
        task
        + "\nReturn a JSON object with exactly one field, source, containing standalone Python defining transform(payload)."
    )
    feedback_text = "None yet."
    candidate_id = None
    source = None
    accepted = False
    for attempt in range(3 if live else 2):
        source = None
        try:
            if arm == "dspy":
                source = program(task, feedback_text)
                if not isinstance(source, str):
                    raise ValueError("Candidate source must be text")
            elif live:
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
                source = "def transform(payload):\n    return payload\n" if attempt == 0 else case.CONTROL_SOURCE
            if arm == "ynot":
                result = store.qualify(source, contract, executor, allowance)
                feedback = {"passed": result.promoted, "cases": [case_.model_dump() for case_ in result.receipt.cases]}
                candidate_id = result.capability_id
                (folder / f"qualification-{attempt + 1}.json").write_text(result.model_dump_json(indent=2))
            else:
                feedback = direct_check(source, executor, allowance, case)
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
        previous = (
            "\nPrevious candidate:\n" + (source or "No valid candidate") + "\nHost feedback:\n" + canonical(feedback)
        )
        prompt += previous
        feedback_text = (previous if feedback_text == "None yet." else feedback_text + previous).strip()
    if program is not None:
        program.save(str(folder / "program.json"))
    qualification_seconds = time.monotonic() - started
    reused = fresh_reuse(folder, arm, candidate_id, case=case) if accepted else None
    elapsed = time.monotonic() - started
    record = {
        "arm": arm,
        "case": case.NAME,
        "mode": "live" if live else "scripted_control",
        "attempts": len(attempts),
        "accepted": accepted,
        "attempt_feedback": attempts,
        "qualification_passes": sum(case_["passed"] for case_ in attempts[-1]["cases"]),
        "qualification_cases": len(contract.cases),
        "qualification_executions": allowance.used,
        "source_sha256": hashlib.sha256(source.encode()).hexdigest() if isinstance(source, str) else None,
        "contract_sha256": contract.digest,
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
        record["revocation_control"] = fresh_reuse(folder, arm, candidate_id, revoked=True, case=case)
    (folder / "result.json").write_text(json.dumps(record, indent=2) + "\n")
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--store", type=Path, required=True)
    parser.add_argument("--case", choices=sorted(CASES), default=schema_case.NAME)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--model", default="gpt-6-astra")
    parser.add_argument("--reasoning", default="medium")
    parser.add_argument("--order", choices=("direct-first", "ynot-first"), default="direct-first")
    parser.add_argument("--arms", help="Comma-separated live arms in run order, e.g. direct,dspy,ynot")
    parser.add_argument("--reuse", choices=ARMS, help=argparse.SUPPRESS)
    parser.add_argument("--capability-id", default="", help=argparse.SUPPRESS)
    parser.add_argument("--revoked", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    case = CASES[args.case]
    if args.reuse:
        print(json.dumps(reuse(args.store, args.reuse, args.capability_id, revoked=args.revoked, case=case)))
        return
    # Every invocation has a fresh store; repeated demos cannot revive a revoked ID.
    folder = args.store.resolve() / uuid4().hex[:12]
    if args.arms:
        arms = tuple(arm.strip() for arm in args.arms.split(","))
        if len(set(arms)) != len(arms) or any(arm not in ARMS for arm in arms):
            parser.error("--arms needs distinct arms from " + ", ".join(ARMS))
    else:
        arms = ("direct", "ynot") if args.order == "direct-first" else ("ynot", "direct")
    if not args.live:
        arms = ("ynot",)
    result = {
        "case": case.NAME,
        "mode": "live_pair" if args.live else "scripted_control",
        "model": args.model if args.live else None,
        "reasoning": args.reasoning if args.live else None,
        "order": list(arms),
        "results": [],
    }
    for arm in arms:
        try:
            arm_result = run_arm(
                folder / arm, arm, live=args.live, model=args.model, reasoning=args.reasoning, case=case
            )
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
    holdouts = len(case.later_jobs())
    if any(
        not arm.get("accepted") or arm.get("reuse", {}).get("heldout_passes") != holdouts for arm in result["results"]
    ):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
