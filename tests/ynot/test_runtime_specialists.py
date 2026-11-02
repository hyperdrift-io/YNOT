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
        "specialist_returned",
        "specialist_created",
        "specialist_returned",
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


def test_one_call_specialist_is_rejected_before_creation():
    supervisor = Supervisor(DummyLM([specialise(call_limit=1)]), {"reader": DummyLM(answer())}, {})
    allowance = Allowance()
    with dspy.context(adapter=dspy.ChatAdapter(use_json_adapter_fallback=False)):
        with pytest.raises(dspy.AdapterParseError, match="call_limit"):
            supervisor("Find evidence", allowance=allowance)
    assert supervisor.created == []
    assert allowance.used_model_calls == 1  # Only the supervisor's planning call.
    assert not allowance.exhausted


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
    allowance = Allowance(model_calls=1)
    supervisor = Supervisor(DummyLM([stop(), stop()]), {}, {})
    with dspy.context(adapter=dspy.ChatAdapter()):
        assert supervisor("Find evidence", allowance=allowance).status == "stopped"
        result = supervisor("Find evidence", allowance=allowance)
    assert result.status == "limit"
    assert allowance.used_model_calls == 1
    assert result.checkpoint == []


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


def test_planner_sees_remaining_tool_calls_after_research():
    requests, called = [], []
    replies = DummyLM([specialise(tools=["read"], call_limit=3), stop("Evidence complete")])

    class RecordingPlanner:
        def complete(self, request):
            requests.append(request)
            return replies(request, cache=False)

    def read(query: str) -> str:
        called.append(query)
        return "Public evidence"

    worker = DummyLM(
        [
            {"next_thought": "Read source", "next_tool_name": "read", "next_tool_args": {"query": "q"}},
            {"next_thought": "Have source", "next_tool_name": "finish", "next_tool_args": {}},
            {"plan": "Retain source", "finding": "Public evidence"},
        ]
    )
    planner = dspy.BaseLM("dummy", engine=RecordingPlanner(), cache=False)
    supervisor = Supervisor(planner, {"reader": worker}, {"read": read})
    allowance = Allowance(tool_calls=1)
    with dspy.context(adapter=dspy.ChatAdapter()):
        result = supervisor("Find evidence", allowance=allowance)
    assert result.status == "stopped"
    assert called == ["q"] and allowance.used_tool_calls == 1
    first = requests[0].messages[-1].parts[0].text
    second = requests[1].messages[-1].parts[0].text
    assert "[[ ## remaining_tools ## ]]\n1" in first
    assert "[[ ## remaining_tools ## ]]\n0" in second


def test_iteration_limit_keeps_observations_and_can_continue_same_worker():
    planner = DummyLM(
        [
            specialise(tools=["read"], call_limit=2),
            {"action": "continue", "reason": "The source leaves an accessible question", "spec": None},
            stop("The required evidence is retained"),
        ]
    )
    worker = DummyLM(
        [
            {"next_thought": "Read source", "next_tool_name": "read", "next_tool_args": {"query": "q"}},
            {"plan": "Incomplete", "finding": "A plausible answer; source detail omitted"},
            *answer("Qualified answer from retained source"),
        ]
    )

    def read(query: str) -> str:
        return "Source: access requires the paid tier; see the account-specific conditions."

    requests = []

    class RecordingPlanner:
        def complete(self, request):
            requests.append(request)
            return planner(request, cache=False)

    supervisor = Supervisor(
        dspy.BaseLM("dummy", engine=RecordingPlanner(), cache=False), {"reader": worker}, {"read": read}
    )
    allowance = Allowance()
    with dspy.context(adapter=dspy.ChatAdapter()):
        result = supervisor("Find a service within the permitted tier", allowance=allowance)
    assert result.status == "stopped"
    assert len(supervisor.created) == 1
    first, second = result.checkpoint
    assert first["execution"]["termination"] == "iteration_limit"
    assert first["execution"]["model_calls"] == 2
    assert first["execution"]["observations"][0]["observation"].startswith("Source: access")
    assert second["execution"]["termination"] == "finished"
    planning_input = requests[1].messages[-1].parts[0].text
    assert "iteration_limit" in planning_input
    assert "access requires the paid tier" in planning_input
    continuation = supervisor.created[0].react.lm.engine.lm.history[-2]["messages"]
    assert "access requires the paid tier" in json.dumps(continuation)
    assert "thought_0" not in json.dumps(first["execution"])
    assert result.events[2]["event"] == "specialist_continued"
    assert allowance.used_model_calls == 7 and allowance.used_tool_calls == 1


def test_larger_worker_allowance_is_bounded_and_deliberate_finish_stays_short():
    supervisor = Supervisor(DummyLM([specialise(call_limit=6), stop()]), {"reader": DummyLM(answer())}, {})
    allowance = Allowance(model_calls=8)
    with dspy.context(adapter=dspy.ChatAdapter()):
        result = supervisor("Answer from the supplied evidence", allowance=allowance)
    assert len(supervisor.created) == 1
    assert result.checkpoint[0]["execution"]["termination"] == "finished"
    assert result.checkpoint[0]["execution"]["call_limit"] == 6
    assert allowance.used_model_calls == 4


def test_worker_must_leave_capacity_for_supervisor_assessment():
    supervisor = Supervisor(DummyLM([specialise(call_limit=3)]), {"reader": DummyLM(answer())}, {})
    with dspy.context(adapter=dspy.ChatAdapter()), pytest.raises(ValueError, match="assessment"):
        supervisor("Investigate", allowance=Allowance(model_calls=4))
    assert supervisor.created == []


def test_continue_cannot_create_a_worker_or_replace_its_authority():
    supervisor = Supervisor(DummyLM([{"action": "continue", "reason": "Try", "spec": None}]), {}, {})
    with dspy.context(adapter=dspy.ChatAdapter()), pytest.raises(ValueError, match="existing worker"):
        supervisor("Investigate")
    planner = DummyLM(
        [specialise(), {"action": "continue", "reason": "Expand authority", "spec": worker_spec(tools=["send"])}]
    )
    supervisor = Supervisor(planner, {"reader": DummyLM(answer())}, {})
    with dspy.context(adapter=dspy.ChatAdapter()), pytest.raises(ValueError, match="replacement spec"):
        supervisor("Investigate")
    assert len(supervisor.created) == 1


def test_unavailable_replacement_does_not_change_worker_continuation():
    planner = DummyLM(
        [
            specialise(),
            specialise(model_alias="busy", purpose="Unavailable replacement"),
            {"action": "continue", "reason": "Use the available worker", "spec": None},
            stop(),
        ]
    )
    requests = []

    class RecordingPlanner:
        def complete(self, request):
            requests.append(request)
            return planner(request, cache=False)

    supervisor = Supervisor(
        dspy.BaseLM("dummy", engine=RecordingPlanner(), cache=False),
        {"reader": DummyLM(answer() + answer()), "busy": DummyLM([])},
        {},
        available=lambda a: a != "busy",
    )
    with dspy.context(adapter=dspy.ChatAdapter()):
        result = supervisor("Investigate")
    assert len(supervisor.created) == 1
    assert result.checkpoint[-1]["purpose"] == "Check a specific gap"
    assert result.status == "stopped"

    continuation_input = requests[2].messages[-1].parts[0].text
    active = continuation_input.split("[[ ## current_worker ## ]]")[1].split("[[ ## remaining ## ]]")[0]
    assert '"model_alias":"reader"' in active
    assert "busy" not in active


def test_structured_dated_tool_evidence_survives_planner_handoff():
    from datetime import date

    from pydantic import BaseModel

    class Evidence(BaseModel):
        checked_at: date
        conditions: list[str]

    supplied = Evidence(checked_at=date(2026, 11, 2), conditions=["Account approval required"])

    def read(query: str) -> Evidence:
        return supplied

    worker = DummyLM(
        [
            {"next_thought": "Read", "next_tool_name": "read", "next_tool_args": {"query": "q"}},
            {"plan": "Retain", "finding": "Check the condition"},
        ]
    )
    planner = DummyLM([specialise(tools=["read"]), stop()])
    supervisor = Supervisor(planner, {"reader": worker}, {"read": read})
    with dspy.context(adapter=dspy.ChatAdapter()):
        result = supervisor("Assess conditions")
    supplied.conditions.clear()
    observed = result.checkpoint[0]["execution"]["observations"][0]["observation"]
    assert observed == {"checked_at": "2026-11-02", "conditions": ["Account approval required"]}
    assert result.status == "stopped"
