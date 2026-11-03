"""Accumulated work per arm, composition offered equally, failures kept as feedback."""

import importlib.util
import json
import shutil
import subprocess
import sys

import pytest

from examples.ynot import capability_accumulation as demo
from examples.ynot import composed_case, schema_case, strict_schema_case


class InProcessExecutor:
    policy = "test-in-process"

    def __call__(self, source, payload):
        namespace = {}
        exec(source, namespace)
        return json.loads(json.dumps(namespace["transform"](json.loads(json.dumps(payload)))))


@pytest.fixture
def fast(monkeypatch):
    monkeypatch.setattr(demo, "PyodideExecutor", InProcessExecutor)
    monkeypatch.setattr(demo, "fresh_reuse", lambda folder, arm, job, capability_id: {"heldout_passes": None})


@pytest.mark.parametrize("arm", ["direct", "ynot"])
def test_scripted_arm_accumulates_and_composes_the_third_job(tmp_path, fast, arm):
    folder = tmp_path / arm
    folder.mkdir()
    records = [
        demo.run_job(folder, arm, job, live=False, host=None, program=None)
        for job in (schema_case.NAME, strict_schema_case.NAME, composed_case.NAME)
    ]
    assert [record["accepted"] for record in records] == [True, True, True]
    assert [record["mode"] for record in records] == ["source", "source", "compose"]
    assert records[2]["compose"] == list(composed_case.STEPS)
    assert records[2]["catalogue_offered"] == [schema_case.NAME, strict_schema_case.NAME]
    assert not records[2]["attempt_feedback"][0]["passed"] and records[2]["attempts"] == 2
    names = [entry["name"] for entry in demo.catalogue(folder)]
    assert names == [schema_case.NAME, strict_schema_case.NAME, composed_case.NAME]
    if arm == "ynot":
        saved = json.loads(next((folder / "store").rglob(f"{records[2]['capability_id']}.json")).read_text())
        assert saved["kind"] == "composite"
    else:
        assert json.loads((folder / "library" / f"{composed_case.NAME}.json").read_text()) == {
            "compose": list(composed_case.STEPS)
        }
        assert len(demo.library_sources(folder, [composed_case.NAME])) == 2


def test_unknown_or_empty_composition_is_feedback_not_a_crash(tmp_path, fast):
    class Host:
        def __init__(self):
            self.calls = []

        def invoke(self, prompt, **kwargs):
            self.calls.append({"usage": [{"input_tokens": 1, "output_tokens": 1}]})
            return json.dumps({"source": None, "compose": ["missing"]}), {}

    folder = tmp_path / "direct"
    folder.mkdir()
    record = demo.run_job(folder, "direct", strict_schema_case.NAME, live=True, host=Host(), program=None)
    assert not record["accepted"] and record["attempts"] == 3 and record["model_calls"] == 3
    assert all(item["error"] == "KeyError" for item in record["attempt_feedback"])
    assert demo.catalogue(folder) == []


def test_direct_reuse_chains_the_saved_library(tmp_path, monkeypatch):
    monkeypatch.setattr(demo, "PyodideExecutor", InProcessExecutor)
    folder = tmp_path / "direct"
    (folder / "library").mkdir(parents=True)
    (folder / "library" / f"{schema_case.NAME}.py").write_text(schema_case.CONTROL_SOURCE)
    result = demo.reuse(folder, "direct", schema_case.NAME, None)
    assert result["heldout_passes"] == result["heldout_cases"] == 4
    assert result["executions"] == 4


def test_dspy_program_parses_none_and_names(tmp_path):
    from examples.ynot.live_codex import CodexHost

    host = CodexHost(tmp_path / "model", max_invocations=3)

    def invoke(prompt, **kwargs):
        record = {"usage": [{"input_tokens": 1, "output_tokens": 1}]}
        host.calls.append(record)
        return "[[ ## source ## ]]\nnone\n\n[[ ## compose ## ]]\na-job, b-job\n\n[[ ## completed ## ]]", record

    host.invoke = invoke
    program = demo.build_dspy_program(host)
    assert program("task", "[]", "None yet.") == (None, ["a-job", "b-job"])
    program.save(str(tmp_path / "program.json"))
    assert json.loads((tmp_path / "program.json").read_text()).get("lm") is None


@pytest.mark.skipif(
    not (shutil.which("deno") or importlib.util.find_spec("deno")), reason="Optional Deno runtime required"
)
def test_control_runs_every_job_in_the_real_boundary_and_composes(tmp_path):
    completed = subprocess.run(
        [sys.executable, "-m", "examples.ynot.capability_accumulation", "--store", str(tmp_path)],
        capture_output=True,
        text=True,
        check=True,
        timeout=900,
    )
    report = json.loads(completed.stdout)
    records = report["results"]["ynot"]
    assert [record["job"] for record in records] == list(demo.JOBS)
    assert all(record["accepted"] for record in records)
    assert [record["mode"] for record in records] == ["source", "source", "source", "compose"]
    for record in records:
        assert record["reuse"]["heldout_passes"] == record["reuse"]["heldout_cases"] >= 4
