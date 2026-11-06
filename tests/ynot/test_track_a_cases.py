"""Track A jobs: real fixtures, hidden holdouts, a second behaviour measure."""

import json

import pytest

from examples.ynot import capability_accumulation as demo
from examples.ynot import mcp_tools_case, openapi_document_case, suite_migration_case
from examples.ynot.capability_lifecycle import canonical

CASES = (mcp_tools_case, suite_migration_case, openapi_document_case)


def run(source, payload):
    namespace = {}
    exec(source, namespace)
    return json.loads(json.dumps(namespace["transform"](json.loads(json.dumps(payload)))))


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.NAME)
def test_control_passes_every_host_case_and_holdout_and_behaves(case):
    for acceptance in case.contract().cases:
        assert canonical(run(case.CONTROL_SOURCE, acceptance.payload)) == canonical(acceptance.expected)
    holdouts = case.later_jobs()
    assert holdouts
    for index, acceptance in enumerate(holdouts):
        output = run(case.CONTROL_SOURCE, acceptance.payload)
        assert canonical(output) == canonical(acceptance.expected)
        assert case.behaviour(index, output) == case.behaviour(index, acceptance.expected)
        assert case.behaviour(index, output)[0]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.NAME)
def test_holdouts_are_disjoint_from_host_cases_and_identity_fails(case):
    hosts = {canonical(c.payload) for c in case.contract().cases}
    assert not hosts & {canonical(c.payload) for c in case.later_jobs()}
    identity = "def transform(payload):\n    return payload\n"
    assert any(canonical(run(identity, c.payload)) != canonical(c.expected) for c in case.contract().cases)
    holdouts = case.later_jobs()
    assert not all(case.behaviour(i, run(identity, c.payload))[0] for i, c in enumerate(holdouts))


def test_population_sizes_match_the_record():
    assert len(mcp_tools_case.tools()) == 29 and len(mcp_tools_case.later_jobs()) == 21
    assert sum(1 + len(tool["same_schema_as"]) for tool in mcp_tools_case.tools()) == 36
    assert len(suite_migration_case.groups()) == 146 and len(suite_migration_case.later_jobs()) == 136
    assert len(json.loads(suite_migration_case.FIXTURE.read_text())["excluded"]) == 15
    assert len(openapi_document_case.documents()) == 21 and len(openapi_document_case.later_jobs()) == 16
    assert {tool["server"] for tool in mcp_tools_case.tools()} == {
        "crunch-accounting-mcp",
        "deputy-workforce-mcp",
        "traction",
    }


def test_observations_are_live_rejections():
    for case in (mcp_tools_case, openapi_document_case):
        observation = case.initial_observation()
        assert observation["client_error"]["status"] == 400
        assert observation["client_error"]["code"] == "invalid_json_schema"
    assert "items" in suite_migration_case.initial_observation()["error"] or suite_migration_case.initial_observation()


def test_behaviour_measures_catch_wording_and_semantics():
    tool = mcp_tools_case.later_tools()[0]
    loose = json.loads(json.dumps(tool["expected"]))
    loose["additionalProperties"] = True
    assert not mcp_tools_case.behaviour(0, loose)[0]
    group = suite_migration_case.later_groups()[0]
    broken = json.loads(json.dumps(group["expected"]))
    broken["not"] = {}
    ok, reason = suite_migration_case.behaviour(0, broken)
    assert not ok and reason.startswith("verdict changed")


def test_track_a_jobs_are_registered_and_the_reuse_record_carries_behaviour(tmp_path, monkeypatch):
    class InProcessExecutor:
        policy = "test-in-process"

        def __call__(self, source, payload):
            return run(source, payload)

    monkeypatch.setattr(demo, "PyodideExecutor", InProcessExecutor)
    assert all(case.NAME in demo.JOBS for case in CASES)
    assert demo.TRACK_A_JOBS.split(",") == [case.NAME for case in CASES]
    folder = tmp_path / "direct"
    (folder / "library").mkdir(parents=True)
    (folder / "library" / f"{mcp_tools_case.NAME}.py").write_text(mcp_tools_case.CONTROL_SOURCE)
    result = demo.reuse(folder, "direct", mcp_tools_case.NAME, None)
    assert result["heldout_passes"] == result["heldout_cases"] == 21
    assert result["behaviour_passes"] == 21 and result["behaviour_failures"] == []
