"""Composition reuses accepted capabilities under a new contract without generating code."""

import json

import pytest

from ynot import AcceptanceCase, CapabilityContract, CapabilityStore, ExecutionAllowance
from ynot.capabilities import COMPOSITE_MARKER, CapabilityError


class InProcessExecutor:
    policy = "test-in-process"

    def __init__(self):
        self.calls = 0

    def __call__(self, source, payload):
        self.calls += 1
        namespace = {}
        exec(source, namespace)
        return json.loads(json.dumps(namespace["transform"](json.loads(json.dumps(payload)))))


ADD = "def transform(payload):\n    return {'value': payload['value'] + 1}\n"
DOUBLE = "def transform(payload):\n    return {'value': payload['value'] * 2}\n"
NUMBER = {"type": "object", "properties": {"value": {"type": "integer"}}, "required": ["value"]}


def contract(name, pairs):
    return CapabilityContract(name, "1", NUMBER, NUMBER, [AcceptanceCase({"value": a}, {"value": b}) for a, b in pairs])


ADD_CONTRACT = contract("add-one", [(1, 2), (5, 6)])
DOUBLE_CONTRACT = contract("double", [(1, 2), (5, 10)])
ADD_THEN_DOUBLE = contract("add-then-double", [(1, 4), (5, 12), (0, 2)])
DOUBLE_THEN_ADD = contract("double-then-add", [(1, 3), (5, 11)])


@pytest.fixture
def store(tmp_path):
    executor = InProcessExecutor()
    store = CapabilityStore(tmp_path, "tests", executor.policy)
    allowance = ExecutionAllowance(100)
    add = store.qualify(ADD, ADD_CONTRACT, executor, allowance).capability_id
    double = store.qualify(DOUBLE, DOUBLE_CONTRACT, executor, allowance).capability_id
    return store, executor, allowance, add, double


def test_composition_qualifies_runs_after_reload_and_counts_each_member(store, tmp_path):
    store_, executor, allowance, add, double = store
    result = store_.compose([add, double], ADD_THEN_DOUBLE, executor, allowance)
    assert result.promoted and all(case.passed for case in result.receipt.cases)
    assert result.receipt.executions == 3
    before = allowance.used
    fresh = CapabilityStore(tmp_path, "tests", executor.policy)
    assert fresh.run(result.capability_id, {"value": 10}, ADD_THEN_DOUBLE, executor, ExecutionAllowance(2)) == {
        "value": 22
    }
    assert allowance.used == before
    saved = json.loads((store_._path(result.capability_id)).read_text())
    assert saved["kind"] == "composite" and saved["source"].startswith(COMPOSITE_MARKER)
    assert "def " not in saved["source"]


def test_order_is_part_of_the_identity(store):
    store_, executor, allowance, add, double = store
    first = store_.compose([add, double], ADD_THEN_DOUBLE, executor, allowance)
    second = store_.compose([double, add], DOUBLE_THEN_ADD, executor, allowance)
    assert first.promoted and second.promoted and first.capability_id != second.capability_id
    wrong = store_.compose([double, add], ADD_THEN_DOUBLE, executor, allowance)
    assert not wrong.promoted and wrong.capability_id is None


def test_revoking_a_member_blocks_the_composite_and_future_composition(store):
    store_, executor, allowance, add, double = store
    composite = store_.compose([add, double], ADD_THEN_DOUBLE, executor, allowance).capability_id
    store_.revoke(add, "withdrawn")
    with pytest.raises(CapabilityError):
        store_.run(composite, {"value": 1}, ADD_THEN_DOUBLE, executor, allowance)
    with pytest.raises(CapabilityError):
        store_.compose([add, double], DOUBLE_THEN_ADD, executor, allowance)


def test_member_allowance_exhaustion_and_tampering_are_not_hidden(store):
    store_, executor, allowance, add, double = store
    composite = store_.compose([add, double], ADD_THEN_DOUBLE, executor, allowance).capability_id
    with pytest.raises(Exception, match="allowance"):
        store_.run(composite, {"value": 1}, ADD_THEN_DOUBLE, executor, ExecutionAllowance(1))
    path = store_._path(double)
    saved = json.loads(path.read_text())
    saved["source"] = DOUBLE.replace("* 2", "* 3")
    path.write_text(json.dumps(saved))
    with pytest.raises(CapabilityError):
        store_.run(composite, {"value": 1}, ADD_THEN_DOUBLE, executor, allowance)


def test_invalid_steps_are_rejected_and_a_manifest_cannot_qualify_as_source(store):
    store_, executor, allowance, add, _double = store
    with pytest.raises(CapabilityError):
        store_.compose([], ADD_THEN_DOUBLE, executor, allowance)
    with pytest.raises(CapabilityError):
        store_.compose([add, "0" * 64], ADD_THEN_DOUBLE, executor, allowance)
    manifest = COMPOSITE_MARKER + json.dumps({"compose": [{"capability_id": add, "contract_sha256": "x"}]})
    assert not store_.qualify(manifest, ADD_THEN_DOUBLE, executor, allowance).promoted


def test_nested_composition_runs_every_leaf(store):
    store_, executor, allowance, add, double = store
    inner = store_.compose([add, double], ADD_THEN_DOUBLE, executor, allowance).capability_id
    outer_contract = contract("add-double-add", [(1, 5), (5, 13)])
    outer = store_.compose([inner, add], outer_contract, executor, allowance)
    assert outer.promoted
    used = ExecutionAllowance(3)
    assert store_.run(outer.capability_id, {"value": 2}, outer_contract, executor, used) == {"value": 7}
    assert used.used == 3
