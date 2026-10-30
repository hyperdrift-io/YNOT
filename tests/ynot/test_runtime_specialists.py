import json

import pytest

import dspy
from dspy.utils.dummies import DummyLM
from examples.ynot.runtime_specialists import Allowance, Supervisor, scripted_demo


def worker_spec(**changes):
    return {
        "purpose": "Check a specific gap",
        "evidence_gap": "Need a source",
        "instructions": "Read and cite the source.",
        "model_alias": "reader",
        "tools": [],
        "output": "finding",
        "call_limit": 2,
        **changes,
    }


def specialise(**changes):
    return {"action": "specialise", "reason": "A missing capability is needed", "spec": worker_spec(**changes)}


def stop(reason="No supported opportunity"):
    return {"action": "stop", "reason": reason, "spec": None}


def answer(finding="Evidence found"):
    return [
        {"next_thought": "Retained context is sufficient", "next_tool_name": "finish", "next_tool_args": {}},
        {"plan": "Do not claim buying intent", "finding": finding},
    ]


def test_runtime_creation_execution_and_checkpoint():
    planner = DummyLM([specialise(), specialise(purpose="Challenge the retained evidence"), stop()])
    supervisor = Supervisor(planner, {"reader": DummyLM(answer("First finding") + answer("Second finding"))}, {})
    assert supervisor.created == []
    with dspy.context(adapter=dspy.ChatAdapter()):
        result = supervisor("Find a useful opportunity")
    assert result.status == "stopped"
    assert len(supervisor.created) == 2
    first, second = supervisor.created
    assert first.signature.instructions == "Read and cite the source."
    assert second is not first
    # Both real ReAct chains executed; the second received the first result.
    messages = second.react.lm.engine.lm.history[0]["messages"]
    assert "First finding" in json.dumps(messages)
    assert [event["event"] for event in result.events] == [
        "specialist_created",
        "specialist_finished",
        "specialist_created",
        "specialist_finished",
    ]
    assert result.checkpoint[-1]["finding"] == "Second finding"


@pytest.mark.parametrize(
    "changes",
    [
        {"tools": ["send_mail"]},
        {"model_alias": "unapproved"},
        {"call_limit": 4},
    ],
)
def test_policy_rejected_before_worker_invocation(changes):
    supervisor = Supervisor(DummyLM([specialise(**changes)]), {"reader": DummyLM(answer())}, {})
    with dspy.context(adapter=dspy.ChatAdapter()), pytest.raises(ValueError):
        supervisor("Find evidence", allowance=Allowance(model_calls=3))
    assert supervisor.created == []


def test_unavailable_model_replans_with_checkpoint():
    planner = DummyLM([specialise(), specialise(model_alias="busy"), specialise(), stop()])
    supervisor = Supervisor(
        planner,
        {"busy": DummyLM([]), "reader": DummyLM(answer("First finding") + answer("Continued finding"))},
        {},
        available=lambda alias: alias != "busy",
    )
    with dspy.context(adapter=dspy.ChatAdapter()):
        result = supervisor("Find evidence", initial_evidence=[{"source": "existing source"}])
    assert len(supervisor.created) == 2
    assert {"event": "unavailable", "model_alias": "busy"} in result.events
    assert result.checkpoint[0] == {"source": "existing source"}
    messages = supervisor.created[-1].react.lm.engine.lm.history[0]["messages"]
    assert "existing source" in json.dumps(messages)
    assert "First finding" in json.dumps(messages)
    assert "busy" in json.dumps(messages)


def test_model_allowance_is_enforced_at_engine_entry():
    allowance = Allowance(model_calls=3)
    supervisor = Supervisor(DummyLM([specialise(), stop()]), {"reader": DummyLM(answer())}, {})
    with dspy.context(adapter=dspy.ChatAdapter()):
        result = supervisor("Find evidence", allowance=allowance)
    assert result.status == "limit"
    assert allowance.used_model_calls == 3
    assert result.checkpoint[-1]["finding"] == "Evidence found"


def test_tool_limit_blocks_callback_and_further_model_calls():
    called = []

    def read(query: str) -> str:
        called.append(query)
        return "source"

    worker = DummyLM([{"next_thought": "Need source", "next_tool_name": "read", "next_tool_args": {"query": "q"}}])
    supervisor = Supervisor(DummyLM([specialise(tools=["read"])]), {"reader": worker}, {"read": read})
    allowance = Allowance(tool_calls=0)
    with dspy.context(adapter=dspy.ChatAdapter()):
        result = supervisor("Find evidence", allowance=allowance)
    assert result.status == "limit"
    assert called == []
    assert result.checkpoint == []
    assert allowance.used_model_calls == 2


def test_insufficient_evidence_stops_without_inventing_a_prospect():
    supervisor = Supervisor(DummyLM([stop("No attributable sources")]), {}, {})
    with dspy.context(adapter=dspy.ChatAdapter()):
        result = supervisor("Find one customer worth pursuing")
    assert result.status == "stopped"
    assert result.checkpoint == []
    assert result.reason == "No attributable sources"
    assert supervisor.created == []


def test_scripted_demo_uses_tools_and_has_explicit_limits():
    result = scripted_demo()
    assert result["mode"] == "scripted_control"
    assert result["status"] == "stopped"
    assert result["usage"] == {"model_calls": 8, "tool_calls": 1}
    assert "Illustrative" in result["checkpoint"][-1]["opportunity"]
