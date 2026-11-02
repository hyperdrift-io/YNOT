"""Exercise the public reference and retain failures in the matched comparison."""

import importlib.util
import json
import shutil
import subprocess
import sys

import pytest

from examples.ynot import capability_lifecycle as demo


@pytest.mark.skipif(
    not (shutil.which("deno") or importlib.util.find_spec("deno")), reason="Optional Deno runtime required"
)
def test_reference_runs_rejection_promotion_fresh_reuse_and_revocation(tmp_path):
    completed = subprocess.run(
        [sys.executable, "-m", "examples.ynot.capability_lifecycle", "--store", str(tmp_path)],
        capture_output=True,
        text=True,
        check=True,
        timeout=180,
    )
    report = json.loads(completed.stdout)
    result = report["results"][0]
    assert report["mode"] == "scripted_control"
    assert result["accepted"] and result["attempts"] == 2
    assert not result["attempt_feedback"][0]["passed"]
    assert result["qualification_executions"] == 14
    assert result["reuse"]["heldout_passes"] == 4
    assert result["reuse"]["executions"] == 4
    assert result["model_calls"] == result["reuse"]["model_calls"] == 0
    assert result["revocation_control"] == {"revocation_blocked": True, "executions": 0}


class IdentityExecutor:
    policy = "test-identity"

    def __call__(self, source, payload):
        return payload


@pytest.mark.parametrize("arm", ["direct", "ynot"])
def test_failed_acquisition_retains_cost_and_result(tmp_path, monkeypatch, arm):
    from examples.ynot import live_codex

    class Host:
        def __init__(self, *args, **kwargs):
            self.calls = []

        def invoke(self, prompt, **kwargs):
            self.calls.append({"usage": [{"input_tokens": 10, "output_tokens": 5}]})
            return json.dumps({"source": "def transform(payload):\n    return payload"}), {}

    monkeypatch.setattr(live_codex, "CodexHost", Host)
    monkeypatch.setattr(demo, "PyodideExecutor", IdentityExecutor)
    result = demo.run_arm(tmp_path / arm, arm, live=True, model="test", reasoning="test")
    assert not result["accepted"]
    assert result["attempts"] == result["model_calls"] == 3
    assert result["qualification_executions"] == 21
    assert result["reuse"] is None
    assert len(result["usage"]) == 3
    assert json.loads((tmp_path / arm / "result.json").read_text()) == result


def test_reuse_failure_keeps_later_cases_and_attempt_counts(tmp_path, monkeypatch):
    class BrokenExecutor:
        policy = "test-failure"

        def __call__(self, source, payload):
            raise RuntimeError("Candidate failed")

    monkeypatch.setattr(demo, "PyodideExecutor", BrokenExecutor)
    (tmp_path / "candidate.py").write_text("unused")
    result = demo.reuse(tmp_path, "direct", None)
    assert result["heldout_passes"] == 0
    assert result["heldout_cases"] == result["executions"] == 4
    assert result["failures"] == ["RuntimeError"] * 4


def test_first_arm_failure_does_not_hide_the_other_arm(tmp_path, monkeypatch, capsys):
    called = []

    def run_arm(folder, arm, **kwargs):
        called.append(arm)
        if arm == "direct":
            folder.mkdir(parents=True)
            raise OSError("Unavailable store")
        return {"arm": arm, "accepted": True, "reuse": {"heldout_passes": 4}}

    monkeypatch.setattr(demo, "run_arm", run_arm)
    monkeypatch.setattr(sys, "argv", ["demo", "--live", "--store", str(tmp_path)])
    with pytest.raises(SystemExit) as failure:
        demo.main()
    assert failure.value.code == 1
    assert called == ["direct", "ynot"]
    report = json.loads(capsys.readouterr().out)
    assert report["results"][0]["error"] == "OSError"
    assert report["results"][1]["accepted"]
