"""The second consumer: strict structured-output normalisation on the same lifecycle."""

import importlib.util
import json
import shutil
import subprocess
import sys

import pytest

from examples.ynot import capability_lifecycle as demo
from examples.ynot import schema_case, strict_schema_case
from ynot import CapabilityStore, ExecutionAllowance


class InProcessExecutor:
    """Test-only executor; the real boundary is exercised by the Deno-backed reference test."""

    policy = "test-in-process"

    def __call__(self, source, payload):
        namespace = {}
        exec(source, namespace)
        return json.loads(json.dumps(namespace["transform"](json.loads(json.dumps(payload)))))


def run_control(source, case):
    executor = InProcessExecutor()
    return [executor(source, acceptance.payload) == acceptance.expected for acceptance in case.contract().cases]


def test_observation_is_the_recorded_strict_client_rejection():
    observation = strict_schema_case.initial_observation()
    assert observation["client_error"]["code"] == "invalid_json_schema"
    assert "additionalProperties" in observation["client_error"]["message"]
    assert "additionalProperties" not in json.dumps(observation["schema"])


def test_control_source_passes_every_qualification_case_and_holdout(tmp_path):
    """Route through the store so its JSON canonicalisation applies, as it does in reuse."""
    executor = InProcessExecutor()
    store = CapabilityStore(tmp_path, demo.SCOPE, executor.policy)
    contract = strict_schema_case.contract()
    allowance = ExecutionAllowance(40)
    result = store.qualify(strict_schema_case.CONTROL_SOURCE, contract, executor, allowance)
    assert result.promoted
    for acceptance in strict_schema_case.later_jobs():
        output = store.run(result.capability_id, acceptance.payload, contract, executor, allowance)
        assert output == acceptance.expected


def test_holdouts_are_disjoint_from_qualification_cases_and_cover_each_rule():
    qualification = {json.dumps(case.payload, sort_keys=True) for case in strict_schema_case.contract().cases}
    holdouts = strict_schema_case.later_jobs()
    assert len(holdouts) >= 4
    assert not qualification & {json.dumps(case.payload, sort_keys=True) for case in holdouts}
    rendered = json.dumps([case.payload for case in holdouts])
    assert '"default"' in rendered and '"anyOf"' in rendered and '"items"' in rendered


def test_identity_candidate_fails_and_control_promotes(tmp_path):
    executor = InProcessExecutor()
    store = CapabilityStore(tmp_path, demo.SCOPE, executor.policy)
    allowance = ExecutionAllowance(40)
    contract = strict_schema_case.contract()
    failed = store.qualify("def transform(payload):\n    return payload\n", contract, executor, allowance)
    assert not failed.promoted
    assert sum(case.passed for case in failed.receipt.cases) == 0
    passed = store.qualify(strict_schema_case.CONTROL_SOURCE, contract, executor, allowance)
    assert passed.promoted
    assert allowance.used == 2 * len(contract.cases)


def test_strict_control_does_not_satisfy_the_nullability_contract():
    assert not all(run_control(strict_schema_case.CONTROL_SOURCE, schema_case))
    assert not all(run_control(schema_case.CONTROL_SOURCE, strict_schema_case))


@pytest.mark.skipif(
    not (shutil.which("deno") or importlib.util.find_spec("deno")), reason="Optional Deno runtime required"
)
def test_case_selection_runs_the_strict_lifecycle_in_the_real_boundary(tmp_path):
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "examples.ynot.capability_lifecycle",
            "--case",
            strict_schema_case.NAME,
            "--store",
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
        check=True,
        timeout=240,
    )
    report = json.loads(completed.stdout)
    result = report["results"][0]
    holdouts = len(strict_schema_case.later_jobs())
    assert report["case"] == result["case"] == strict_schema_case.NAME
    assert result["accepted"] and result["attempts"] == 2
    assert result["qualification_executions"] == 2 * len(strict_schema_case.contract().cases)
    assert result["reuse"]["heldout_passes"] == result["reuse"]["heldout_cases"] == holdouts
    assert result["revocation_control"] == {"revocation_blocked": True, "executions": 0}


def test_dspy_arm_feeds_back_host_results_and_counts_engine_calls(tmp_path, monkeypatch):
    from examples.ynot import live_codex

    class Host:
        def __init__(self, *args, **kwargs):
            self.calls = []

    seen = []

    def build(host):
        def generate(task, feedback):
            host.calls.append({"usage": [{"input_tokens": 7, "output_tokens": 3}]})
            seen.append(feedback)
            return "def transform(payload):\n    return payload"

        generate.save = lambda path: (tmp_path / "saved").write_text(path)
        return generate

    monkeypatch.setattr(live_codex, "CodexHost", Host)
    monkeypatch.setattr(demo, "build_dspy_program", build)
    monkeypatch.setattr(demo, "PyodideExecutor", InProcessExecutor)
    result = demo.run_arm(tmp_path / "dspy", "dspy", live=True, model="test", reasoning="test", case=strict_schema_case)
    assert not result["accepted"]
    assert result["attempts"] == result["model_calls"] == 3
    assert seen[0] == "None yet." and "Host feedback" in seen[1] and seen[2].count("Previous candidate") == 2
    assert (tmp_path / "saved").read_text().endswith("program.json")
    assert result["qualification_executions"] == 3 * len(strict_schema_case.contract().cases)


def test_dspy_program_generates_from_feedback_and_saves_without_the_engine(tmp_path):
    from examples.ynot.live_codex import CodexHost

    host = CodexHost(tmp_path / "model", max_invocations=3)
    prompts = []

    def invoke(prompt, **kwargs):
        prompts.append(prompt)
        record = {"usage": [{"input_tokens": 1, "output_tokens": 1}]}
        host.calls.append(record)
        return "[[ ## source ## ]]\ndef transform(payload):\n    return payload\n\n[[ ## completed ## ]]", record

    host.invoke = invoke
    program = demo.build_dspy_program(host)
    assert program("task text", "host said no").startswith("def transform")
    assert "host said no" in prompts[0] and len(host.calls) == 1
    program.save(str(tmp_path / "program.json"))
    saved = json.loads((tmp_path / "program.json").read_text())
    assert saved.get("lm") is None and "source" in json.dumps(saved)
    assert program("task text", "again").startswith("def transform")  # the engine is still attached


def test_dspy_arm_is_live_only(tmp_path):
    with pytest.raises(ValueError):
        demo.run_arm(tmp_path / "dspy", "dspy", live=False, model="x", reasoning="x")


def test_arms_option_rejects_duplicates_and_unknown_names(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["demo", "--live", "--store", str(tmp_path), "--arms", "direct,direct"])
    with pytest.raises(SystemExit) as failure:
        demo.main()
    assert failure.value.code == 2
