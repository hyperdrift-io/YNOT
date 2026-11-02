import json
import os
import subprocess
import sys
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest
from jsonschema import ValidationError
from referencing.exceptions import Unresolvable

from ynot.capabilities import (
    AcceptanceCase,
    CapabilityContract,
    CapabilityError,
    CapabilityStore,
    ExecutionAllowance,
    ExecutionLimitError,
)

SOURCE = 'def transform(payload):\n    return {"total": payload["left"] + payload["right"]}\n'
INPUT_SCHEMA = {
    "type": "object",
    "properties": {"left": {"type": "integer"}, "right": {"type": "integer"}},
    "required": ["left", "right"],
    "additionalProperties": False,
}
OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {"total": {"type": "integer"}},
    "required": ["total"],
    "additionalProperties": False,
}


def contract(version="1", cases=None):
    return CapabilityContract(
        "addition",
        version,
        INPUT_SCHEMA,
        OUTPUT_SCHEMA,
        cases
        or [
            AcceptanceCase({"left": 2, "right": 3}, {"total": 5}),
            AcceptanceCase({"left": -2, "right": 1}, {"total": -1}),
        ],
    )


def executor(source, payload):
    # The core injects execution; sandbox execution is tested with its own backend.
    assert source == SOURCE
    return {"total": payload["left"] + payload["right"]}


def store(path, **changes):
    return CapabilityStore(path, **{"scope": "test-owner", "executor_policy": "json-only-v1", **changes})


def qualify(path, *, source=SOURCE):
    saved = store(path)
    result = saved.qualify(source, contract(), executor, ExecutionAllowance(2))
    assert result.promoted
    return saved, result


def test_qualification_persists_contract_receipt_and_reuses_in_fresh_process(tmp_path):
    saved, result = qualify(tmp_path)
    assert result.receipt.executions == 2
    assert all(case.passed for case in result.receipt.cases)
    assert result.receipt.contract_sha256 == contract().digest
    assert result.receipt.cases_sha256 == contract().cases_digest
    artifact = json.loads(next(saved.path.glob("*.json")).read_text())
    assert "payload" not in artifact["receipt"]
    script = """
import json, sys
from tests.ynot.test_capabilities import contract, executor, store
from ynot.capabilities import ExecutionAllowance
allowance = ExecutionAllowance(1)
output = store(sys.argv[1]).run(sys.argv[2], {"left": 7, "right": 9}, contract(), executor, allowance)
print(json.dumps({"output": output, "used": allowance.used}))
"""
    env = {**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[2])}
    process = subprocess.run(
        [sys.executable, "-c", script, str(tmp_path), result.capability_id],
        capture_output=True,
        text=True,
        check=True,
        env=env,
        timeout=30,
    )
    assert json.loads(process.stdout) == {"output": {"total": 16}, "used": 1}


@pytest.mark.parametrize(
    ("output", "reason"),
    [({"total": 999}, "unexpected_output"), ({"total": "5"}, "invalid_output"), ({"passed": True}, "invalid_output")],
)
def test_failed_host_checks_do_not_promote_or_replace_working_version(tmp_path, output, reason):
    saved, original = qualify(tmp_path)
    allowance = ExecutionAllowance(3)
    result = saved.qualify(SOURCE + "# candidate\n", contract(), lambda *_: output, allowance)
    assert not result.promoted and result.capability_id is None
    assert {case.reason for case in result.receipt.cases} == {reason}
    assert len(list(saved.path.glob("*.json"))) == 1
    assert saved.run(original.capability_id, {"left": 4, "right": 5}, contract(), executor, allowance) == {"total": 9}
    assert allowance.used == 3


def test_executor_errors_are_counted_without_saving_private_exception_values(tmp_path):
    def broken(*_):
        raise RuntimeError("private input was confidential-99301")

    saved = store(tmp_path)
    allowance = ExecutionAllowance(2)
    result = saved.qualify(SOURCE, contract(), broken, allowance)
    assert not result.promoted and allowance.used == 2
    assert [case.reason for case in result.receipt.cases] == ["executor_error:RuntimeError"] * 2
    assert "confidential-99301" not in result.model_dump_json()
    assert list(saved.path.iterdir()) == []


@pytest.mark.parametrize("change", ["source", "cases_digest", "case_pass", "scope", "policy"])
def test_tampered_artifact_is_rejected_before_execution_or_charge(tmp_path, change):
    saved, result = qualify(tmp_path)
    path = next(saved.path.glob("*.json"))
    artifact = json.loads(path.read_text())
    if change == "source":
        artifact["source"] += "# changed\n"
    elif change == "cases_digest":
        artifact["receipt"]["cases_sha256"] = "0" * 64
    elif change == "case_pass":
        artifact["receipt"]["cases"][0]["passed"] = False
    elif change == "scope":
        artifact["receipt"]["scope"] = "another-owner"
    else:
        artifact["receipt"]["executor_policy"] = "unrestricted"
    path.write_text(json.dumps(artifact))
    called = []
    allowance = ExecutionAllowance(1)
    with pytest.raises(CapabilityError):
        saved.run(
            result.capability_id, {"left": 1, "right": 1}, contract(), lambda *args: called.append(args), allowance
        )
    assert called == [] and allowance.used == 0


@pytest.mark.parametrize("change", ["scope", "policy", "contract_version", "contract_cases", "unknown"])
def test_changed_host_binding_is_rejected_before_execution(tmp_path, change):
    _, result = qualify(tmp_path)
    active = store(tmp_path)
    active_contract = contract()
    capability_id = result.capability_id
    if change == "scope":
        active = store(tmp_path, scope="another-owner")
    elif change == "policy":
        active = store(tmp_path, executor_policy="json-only-v2")
    elif change == "contract_version":
        active_contract = contract(version="2")
    elif change == "contract_cases":
        active_contract = contract(cases=[AcceptanceCase({"left": 4, "right": 6}, {"total": 10})])
    else:
        capability_id = "0" * 64
    called = []
    allowance = ExecutionAllowance(1)
    with pytest.raises(CapabilityError):
        active.run(
            capability_id, {"left": 1, "right": 1}, active_contract, lambda *args: called.append(args), allowance
        )
    assert called == [] and allowance.used == 0


def test_revocation_survives_reload_and_cannot_be_undone_by_requalification(tmp_path):
    saved, result = qualify(tmp_path)
    saved.revoke(result.capability_id, "Contract no longer supported")
    fresh = store(tmp_path)
    allowance = ExecutionAllowance(3)
    with pytest.raises(CapabilityError, match="revoked"):
        fresh.run(result.capability_id, {"left": 1, "right": 1}, contract(), executor, allowance)
    with pytest.raises(CapabilityError, match="revoked"):
        fresh.qualify(SOURCE, contract(), executor, allowance)
    fresh.revoke(result.capability_id, "Idempotent")
    assert allowance.used == 0


def test_partial_qualification_exhaustion_never_promotes(tmp_path):
    saved = store(tmp_path)
    allowance = ExecutionAllowance(1)
    with pytest.raises(ExecutionLimitError):
        saved.qualify(SOURCE, contract(), executor, allowance)
    assert allowance.used == 1 and list(saved.path.iterdir()) == []


def test_executor_budget_exhaustion_stops_qualification(tmp_path):
    def exhausted(*_):
        raise ExecutionLimitError("Shared execution allowance exhausted")

    saved = store(tmp_path)
    allowance = ExecutionAllowance(2)
    with pytest.raises(ExecutionLimitError):
        saved.qualify(SOURCE, contract(), exhausted, allowance)
    assert allowance.used == 1 and list(saved.path.iterdir()) == []


def test_reuse_cannot_execute_after_allowance_is_spent(tmp_path):
    saved, result = qualify(tmp_path)
    allowance = ExecutionAllowance(0)
    called = []
    with pytest.raises(ExecutionLimitError):
        saved.run(
            result.capability_id, {"left": 1, "right": 1}, contract(), lambda *args: called.append(args), allowance
        )
    assert allowance.used == 0 and called == []


def test_invalid_reuse_input_does_not_consume_allowance_and_invalid_output_does(tmp_path):
    saved, result = qualify(tmp_path)
    allowance = ExecutionAllowance(1)
    with pytest.raises(ValidationError):
        saved.run(result.capability_id, {"left": "one", "right": 1}, contract(), executor, allowance)
    assert allowance.used == 0
    with pytest.raises(ValidationError):
        saved.run(result.capability_id, {"left": 1, "right": 1}, contract(), lambda *_: {"total": "two"}, allowance)
    assert allowance.used == 1


def test_contract_and_case_snapshots_survive_caller_and_backend_mutation(tmp_path):
    payload = {"items": ["original"]}
    expected = {"items": ["original"]}
    schema = {"type": "object", "properties": {"items": {"type": "array", "items": {"type": "string"}}}}
    case = AcceptanceCase(payload, expected)
    frozen = CapabilityContract("copy", "1", schema, schema, [case])
    digest = frozen.digest
    payload["items"].append("caller")
    expected["items"].append("caller")
    schema["properties"]["items"]["type"] = "string"
    frozen.cases[0].payload["items"].append("property")
    frozen.input_schema["properties"].clear()
    assert frozen.digest == digest
    assert frozen.cases[0].payload == {"items": ["original"]}
    with pytest.raises(FrozenInstanceError):
        frozen.version = "2"

    def mutate(_, value):
        value["items"].append("backend")
        return value

    result = store(tmp_path).qualify("def transform(payload): return payload", frozen, mutate, ExecutionAllowance(1))
    assert not result.promoted
    assert frozen.cases[0].payload == frozen.cases[0].expected == {"items": ["original"]}


def test_run_detaches_caller_payload_and_backend_output(tmp_path):
    saved, result = qualify(tmp_path)
    payload = {"left": 3, "right": 5}
    returned = {"total": 8}

    def backend(_, value):
        value["left"] = 99
        return returned

    output = saved.run(result.capability_id, payload, contract(), backend, ExecutionAllowance(1))
    returned["total"] = 999
    assert output == {"total": 8} and payload == {"left": 3, "right": 5}


def test_saved_receipt_omits_raw_acceptance_values(tmp_path):
    secret = "private-case-value-04851"
    frozen = CapabilityContract("copy", "1", {"type": "string"}, {"type": "string"}, [AcceptanceCase(secret, secret)])
    saved = store(tmp_path)
    result = saved.qualify(
        "def transform(payload): return payload", frozen, lambda _, value: value, ExecutionAllowance(1)
    )
    assert result.promoted
    assert secret not in next(saved.path.glob("*.json")).read_text()


def test_failed_atomic_replace_leaves_previous_artifact_intact(tmp_path, monkeypatch):
    saved, result = qualify(tmp_path)
    path = next(saved.path.glob("*.json"))
    before = path.read_bytes()

    def fail(*_):
        raise OSError("replacement failed")

    monkeypatch.setattr("ynot.capabilities.os.replace", fail)
    with pytest.raises(OSError):
        saved.revoke(result.capability_id, "try revoke")
    assert path.read_bytes() == before
    assert list(saved.path.iterdir()) == [path]
    assert saved.run(result.capability_id, {"left": 1, "right": 2}, contract(), executor, ExecutionAllowance(1)) == {
        "total": 3
    }


def test_exact_acceptance_does_not_treat_boolean_as_number(tmp_path):
    frozen = CapabilityContract("identity", "1", True, True, [AcceptanceCase(1, 1)])
    result = store(tmp_path).qualify(
        "def transform(payload): return True", frozen, lambda *_: True, ExecutionAllowance(1)
    )
    assert not result.promoted


@pytest.mark.parametrize("value", [float("nan"), float("inf"), {1: "not a JSON key"}, (1, 2)])
def test_non_json_cases_are_rejected(value):
    with pytest.raises(CapabilityError):
        AcceptanceCase(value, None)


def test_contract_rejects_remote_schema_resolution():
    with pytest.raises(CapabilityError, match="local JSON pointers"):
        CapabilityContract("remote", "1", {"$ref": "https://example.invalid/schema"}, True, [AcceptanceCase({}, {})])


def test_empty_acceptance_set_cannot_qualify_by_vacuous_truth():
    with pytest.raises(CapabilityError, match="at least one"):
        CapabilityContract("empty", "1", True, True, [])


def test_local_schema_references_and_literal_ref_fields_are_supported(tmp_path):
    schema = {
        "type": "object",
        "$defs": {"link": {"type": "string"}},
        "properties": {"$ref": {"$ref": "#/$defs/link"}},
        "required": ["$ref"],
        "additionalProperties": False,
    }
    payload = {"$ref": "https://example.invalid/a-data-value"}
    frozen = CapabilityContract("literal-ref", "1", schema, {"const": payload}, [AcceptanceCase(payload, payload)])
    result = store(tmp_path).qualify(
        "def transform(payload): return payload", frozen, lambda _, value: value, ExecutionAllowance(1)
    )
    assert result.promoted


def test_indirect_remote_schema_reference_cannot_fetch(monkeypatch):
    requests = []

    def forbidden(*args, **kwargs):
        requests.append(args)
        raise AssertionError("A host schema must not cause network access")

    monkeypatch.setattr("urllib.request.urlopen", forbidden)
    schema = {"$ref": "#/custom/schema", "custom": {"schema": {"$ref": "https://example.invalid/schema"}}}
    with pytest.raises(Unresolvable):
        CapabilityContract("indirect", "1", schema, True, [AcceptanceCase({}, {})])
    assert requests == []
