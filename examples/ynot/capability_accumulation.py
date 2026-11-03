"""Run several development jobs in sequence so each arm's accepted work accumulates.

Every arm keeps what it accepted: YNOT in one capability store, the direct and
DSPy baselines in one library of saved files. Later jobs receive a catalogue of
that work and may return a composition of named entries instead of new code.
Composition is equal across arms: the store qualifies a composite under the new
contract; the baselines chain their saved files through the same executor.
Default: deterministic control (YNOT arm only). --live: independent model runs.
"""

import argparse
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path
from uuid import uuid4

from examples.ynot import composed_case, migration_case, schema_case, strict_schema_case
from examples.ynot.capability_lifecycle import ARMS, SCOPE, canonical, direct_check
from ynot import CapabilityStore, ExecutionAllowance, PyodideExecutor
from ynot.capabilities import CapabilityError

JOBS = {module.NAME: module for module in (schema_case, strict_schema_case, migration_case, composed_case)}
DEFAULT_JOBS = ",".join(JOBS)
RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "source": {"type": ["string", "null"]},
        "compose": {"type": ["array", "null"], "items": {"type": "string"}},
    },
    "required": ["source", "compose"],
    "additionalProperties": False,
}


def catalogue(folder):
    """Accepted work so far for one arm: name, task and how to reference it."""
    path = folder / "catalogue.json"
    return json.loads(path.read_text()) if path.exists() else []


def remember(folder, entry):
    entries = [item for item in catalogue(folder) if item["name"] != entry["name"]]
    entries.append(entry)
    (folder / "catalogue.json").write_text(json.dumps(entries, indent=2) + "\n")


def library_sources(folder, names):
    """Ordered sources behind catalogue names; a saved composition expands to its members."""
    sources = []
    for name in names:
        manifest = folder / "library" / f"{name}.json"
        source = folder / "library" / f"{name}.py"
        if manifest.exists():
            sources.extend(library_sources(folder, json.loads(manifest.read_text())["compose"]))
        elif source.exists():
            sources.append(source.read_text())
        else:
            raise KeyError(name)
    return sources


def chain(sources, executor, allowance, payload):
    value = payload
    for source in sources:
        allowance.consume()
        value = executor(source, value)
    return value


def chain_check(sources, executor, allowance, case):
    """Baseline composition check: the same host cases, stage by stage, no saved artefact."""
    contract = case.contract()
    cases = []
    for index, acceptance in enumerate(contract.cases):
        try:
            output = chain(sources, executor, allowance, acceptance.payload)
        except Exception as exc:
            passed, reason = False, f"executor_error:{type(exc).__name__}"
        else:
            passed = canonical(output) == canonical(acceptance.expected)
            reason = "matched" if passed else "unexpected_output"
        cases.append({"index": index, "passed": passed, "reason": reason})
    return {"passed": all(item["passed"] for item in cases), "cases": cases}


def resolve_names(folder, names):
    known = {entry["name"]: entry for entry in catalogue(folder)}
    missing = [name for name in names if name not in known]
    if not names or missing:
        raise KeyError(", ".join(missing) or "empty composition")
    return [known[name] for name in names]


def reuse(folder, arm, job, capability_id):
    """Fresh-process reuse on separately authored holdouts."""
    case = JOBS[job]
    executor = PyodideExecutor()
    holdouts = case.later_jobs()
    allowance = ExecutionAllowance(len(holdouts) * 8)
    results, failures = [], []
    if arm == "ynot":
        store = CapabilityStore(folder / "store", SCOPE, executor.policy)
    else:
        sources = library_sources(folder, [job])
    for acceptance in holdouts:
        try:
            if arm == "ynot":
                output = store.run(capability_id, acceptance.payload, case.contract(), executor, allowance)
            else:
                output = chain(sources, executor, allowance, acceptance.payload)
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


def fresh_reuse(folder, arm, job, capability_id):
    command = [
        sys.executable,
        "-m",
        "examples.ynot.capability_accumulation",
        "--reuse",
        arm,
        "--job",
        job,
        "--store",
        str(folder),
        "--capability-id",
        capability_id or "",
    ]
    try:
        completed = subprocess.run(command, text=True, capture_output=True, check=True, timeout=600)
        return json.loads(completed.stdout)
    except (subprocess.SubprocessError, ValueError) as exc:
        return {"error": type(exc).__name__, "executions": None, "model_calls": 0}


def build_dspy_program(host):
    """Current DSPy: one predictor with a source field and a composition field, no optimiser."""
    import dspy
    from examples.ynot.live_codex import CodexEngine

    class WriteOrCompose(dspy.Signature):
        """Solve the task with standalone Python defining transform(payload), or compose catalogued work."""

        task: str = dspy.InputField()
        catalogue: str = dspy.InputField(desc="JSON list of accepted capabilities you may compose by name, or []")
        feedback: str = dspy.InputField(desc="Previous candidates and host feedback, or none")
        source: str = dspy.OutputField(desc="Standalone Python source defining transform(payload), or the word none")
        compose: str = dspy.OutputField(desc="Comma-separated catalogue names to run in order, or the word none")

    program = dspy.Predict(WriteOrCompose)
    program.set_lm(dspy.BaseLM("custom/codex-cli-default", engine=CodexEngine(host), cache=False, num_retries=0))

    def generate(task, catalogue_json, feedback):
        with dspy.context(adapter=dspy.ChatAdapter()):
            prediction = program(task=task, catalogue=catalogue_json, feedback=feedback)
        source = prediction.source if prediction.source.strip().lower() != "none" else None
        compose = [name.strip() for name in prediction.compose.split(",") if name.strip()]
        if len(compose) == 1 and compose[0].lower() == "none":
            compose = []
        return source, compose

    def save(path):
        lm, program.lm = program.lm, None
        try:
            program.save(path)
        finally:
            program.lm = lm

    generate.save = save
    return generate


def job_prompt(case, entries):
    text = (
        case.TASK
        + "\nObserved failure:\n"
        + canonical(case.initial_observation())
        + "\nRequired behaviour:\n"
        + case.SPECIFICATION
        + "\nYou have up to three candidate attempts. Host acceptance cases and later inputs are withheld."
        + "\nCatalogue of your accepted capabilities (compose by name, in order, or return null):\n"
        + canonical([{"name": e["name"], "task": e["task"]} for e in entries])
    )
    return text


def scripted_candidate(case, attempt):
    if attempt == 0:
        return "def transform(payload):\n    return payload\n", []
    if hasattr(case, "STEPS"):
        return None, list(case.STEPS)
    return case.CONTROL_SOURCE, []


def run_job(folder, arm, job, *, live, host, program, scripted=True):
    case = JOBS[job]
    contract = case.contract()
    job_folder = folder / job
    job_folder.mkdir(parents=True, exist_ok=True)
    (folder / "library").mkdir(exist_ok=True)
    started = time.monotonic()
    executor = PyodideExecutor()
    allowance = ExecutionAllowance(60)
    store = CapabilityStore(folder / "store", SCOPE, executor.policy)
    entries = catalogue(folder)
    prompt = job_prompt(case, entries)
    feedback_text = "None yet."
    attempts, calls_before = [], len(host.calls) if host else 0
    accepted, mode, capability_id, source, compose = False, None, None, None, []
    for attempt in range(3 if live else 2):
        source, compose = None, []
        try:
            if arm == "dspy":
                source, compose = program(
                    prompt, canonical([{"name": e["name"], "task": e["task"]} for e in entries]), feedback_text
                )
            elif live:
                response, _ = host.invoke(
                    prompt
                    + "\nReturn a JSON object with fields source (standalone Python defining transform(payload), or null) and compose (ordered catalogue names, or null). Fill exactly one.",
                    schema=RESPONSE_SCHEMA,
                )
                answer = json.loads(response)
                source, compose = answer.get("source"), answer.get("compose") or []
            else:
                source, compose = scripted_candidate(case, attempt)
            if compose and source:
                raise ValueError("A candidate is either source or a composition")
            if compose:
                chosen = resolve_names(folder, compose)
                if arm == "ynot":
                    result = store.compose([e["reference"] for e in chosen], contract, executor, allowance)
                    feedback = {"passed": result.promoted, "cases": [c.model_dump() for c in result.receipt.cases]}
                    capability_id = result.capability_id
                    (job_folder / f"qualification-{attempt + 1}.json").write_text(result.model_dump_json(indent=2))
                else:
                    feedback = chain_check(library_sources(folder, compose), executor, allowance, case)
            elif isinstance(source, str) and source.strip():
                if arm == "ynot":
                    result = store.qualify(source, contract, executor, allowance)
                    feedback = {"passed": result.promoted, "cases": [c.model_dump() for c in result.receipt.cases]}
                    capability_id = result.capability_id
                    (job_folder / f"qualification-{attempt + 1}.json").write_text(result.model_dump_json(indent=2))
                else:
                    feedback = direct_check(source, executor, allowance, case)
            else:
                raise ValueError("Candidate must supply source or a composition")
        except (KeyError, ValueError, CapabilityError, json.JSONDecodeError) as exc:
            feedback = {"passed": False, "cases": [], "error": type(exc).__name__, "detail": str(exc)[:200]}
        except Exception as exc:
            feedback = {"passed": False, "cases": [], "error": type(exc).__name__}
        attempts.append({"attempt": attempt + 1, "compose": compose or None, **feedback})
        if isinstance(source, str):
            (job_folder / f"candidate-{attempt + 1}.py").write_text(source)
        if compose:
            (job_folder / f"candidate-{attempt + 1}.json").write_text(canonical({"compose": compose}))
        if feedback["passed"]:
            accepted, mode = True, "compose" if compose else "source"
            if arm == "ynot":
                remember(folder, {"name": job, "task": case.TASK, "reference": capability_id, "mode": mode})
            elif compose:
                (folder / "library" / f"{job}.json").write_text(canonical({"compose": compose}))
                remember(folder, {"name": job, "task": case.TASK, "reference": f"library/{job}.json", "mode": mode})
            else:
                (folder / "library" / f"{job}.py").write_text(source)
                remember(folder, {"name": job, "task": case.TASK, "reference": f"library/{job}.py", "mode": mode})
            break
        previous = (
            "\nPrevious candidate:\n"
            + (
                source
                if isinstance(source, str)
                else canonical({"compose": compose})
                if compose
                else "No valid candidate"
            )
            + "\nHost feedback:\n"
            + canonical(feedback)
        )
        prompt += previous
        feedback_text = (previous if feedback_text == "None yet." else feedback_text + previous).strip()
    acquisition_seconds = time.monotonic() - started
    reused = fresh_reuse(folder, arm, job, capability_id) if accepted else None
    calls = host.calls[calls_before:] if host else []
    record = {
        "arm": arm,
        "job": job,
        "mode": mode,
        "compose": compose if (accepted and mode == "compose") else None,
        "attempts": len(attempts),
        "accepted": accepted,
        "attempt_feedback": attempts,
        "qualification_cases": len(contract.cases),
        "qualification_executions": allowance.used,
        "source_sha256": hashlib.sha256(source.encode()).hexdigest() if isinstance(source, str) else None,
        "contract_sha256": contract.digest,
        "acquisition_seconds": round(acquisition_seconds, 3),
        "total_seconds": round(time.monotonic() - started, 3),
        "reuse": reused,
        "model_calls": len(calls),
        "usage": [usage for call in calls for usage in call.get("usage", [])],
        "capability_id": capability_id,
        "catalogue_offered": [e["name"] for e in entries],
        "executor_policy": executor.policy,
    }
    (job_folder / "result.json").write_text(json.dumps(record, indent=2) + "\n")
    return record


def run_arm(folder, arm, jobs, *, live, model, reasoning):
    if arm not in ARMS:
        raise ValueError(f"Unknown arm {arm!r}")
    if arm == "dspy" and not live:
        raise ValueError("The DSPy arm is a live baseline")
    folder.mkdir(parents=True)
    host = program = None
    if live:
        from examples.ynot.live_codex import CodexHost

        host = CodexHost(
            folder / "model",
            max_invocations=3 * len(jobs),
            timeout=180,
            mission_seconds=900 * len(jobs),
            model=model,
            reasoning_effort=reasoning,
        )
        if arm == "dspy":
            program = build_dspy_program(host)
    records = []
    for job in jobs:
        try:
            records.append(run_job(folder, arm, job, live=live, host=host, program=program))
        except Exception as exc:
            records.append({"arm": arm, "job": job, "accepted": False, "error": type(exc).__name__})
        (folder / "arm.json").write_text(json.dumps(records, indent=2) + "\n")
    if program is not None:
        program.save(str(folder / "program.json"))
    return records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--store", type=Path, required=True)
    parser.add_argument("--jobs", default=DEFAULT_JOBS, help="Comma-separated job names in order")
    parser.add_argument("--arms", default="direct,dspy,ynot", help="Comma-separated arms in run order")
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--model", default="gpt-6-astra")
    parser.add_argument("--reasoning", default="medium")
    parser.add_argument("--reuse", choices=ARMS, help=argparse.SUPPRESS)
    parser.add_argument("--job", help=argparse.SUPPRESS)
    parser.add_argument("--capability-id", default="", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.reuse:
        print(json.dumps(reuse(args.store, args.reuse, args.job, args.capability_id)))
        return
    jobs = [job.strip() for job in args.jobs.split(",")]
    if any(job not in JOBS for job in jobs) or len(set(jobs)) != len(jobs):
        parser.error("--jobs needs distinct names from " + ", ".join(JOBS))
    arms = tuple(arm.strip() for arm in args.arms.split(",")) if args.live else ("ynot",)
    if any(arm not in ARMS for arm in arms) or len(set(arms)) != len(arms):
        parser.error("--arms needs distinct arms from " + ", ".join(ARMS))
    folder = args.store.resolve() / uuid4().hex[:12]
    result = {
        "mode": "live_accumulation" if args.live else "scripted_control",
        "model": args.model if args.live else None,
        "reasoning": args.reasoning if args.live else None,
        "jobs": jobs,
        "order": list(arms),
        "results": {},
    }
    for arm in arms:
        result["results"][arm] = run_arm(
            folder / arm, arm, jobs, live=args.live, model=args.model, reasoning=args.reasoning
        )
        (folder / "accumulation.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"evidence": str(folder), **result}, indent=2))
    if not args.live and any(not record.get("accepted") for record in result["results"]["ynot"]):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
