from datetime import date

import pytest

from examples.ynot.runtime_specialists import Allowance
from examples.ynot.service_adviser import (
    Assessment,
    Criterion,
    EvidencePacket,
    Finding,
    FounderNeed,
    ServiceAdviser,
    Source,
    _combine,
    compare,
    demo,
    render,
)


def need(**changes):
    return FounderNeed(
        outcome="Find research services", criteria=[Criterion(id="api", description="Research API")], **changes
    )


def source(id="docs", service="A", day=30):
    return Source(
        id=id,
        service=service,
        url=f"https://{service.lower()}.invalid/docs",
        excerpt="Fictional evidence",
        checked_at=date(2026, 10, day),
    )


def assessment(service="A", status="meets", source_id="docs", **changes):
    return Assessment(
        service=service,
        findings=[Finding(criterion_id="api", status=status, source_id=source_id, detail=f"API {status}")],
        **changes,
    )


def packet(*assessments, sources=None):
    return EvidencePacket(sources=[source()] if sources is None else sources, assessments=list(assessments))


def test_hard_failure_cannot_be_recommended():
    result = compare(need(), packet(assessment(status="fails")))
    assert result["status"] == "no_fit"
    assert result["recommended_service"] is None
    assert result["candidates"][0]["hard_failures"] == ["Research API"]


def test_unknown_requirement_needs_evidence_not_a_positive_claim():
    result = compare(need(), packet(assessment(status="unknown", source_id=None)))
    assert result["status"] == "needs_evidence"
    assert result["recommended_service"] is None
    assert result["questions"] == ["Research API"]


@pytest.mark.parametrize("ref,sources", [("invented", [source()]), ("other", [source("other", "B")])])
def test_fabricated_or_other_service_source_is_rejected(ref, sources):
    with pytest.raises(ValueError, match="source must exist"):
        compare(need(), packet(assessment(source_id=ref), sources=sources))


def test_known_verdict_requires_a_source():
    with pytest.raises(ValueError, match="requires a source"):
        compare(need(), packet(assessment(source_id=None)))


def test_newer_counterevidence_revises_trial_decision():
    old = packet(assessment(), sources=[source(day=29)])
    assert compare(need(), old)["recommended_service"] == "A"
    correction = packet(assessment(status="fails", source_id="correction"), sources=[source("correction")])
    result = compare(need(), _combine([old, correction]))
    assert result["status"] == "no_fit"
    assert result["recommended_service"] is None
    assert len(result["sources"]) == 2


def test_same_date_conflict_is_unknown_instead_of_last_writer_wins():
    a = packet(assessment())
    b = packet(assessment(status="fails", source_id="other"), sources=[source("other")])
    result = compare(need(), _combine([a, b]))
    assert result["status"] == "needs_evidence"
    assert "Conflicting evidence" in result["candidates"][0]["findings"][0]["detail"]


def test_budget_is_a_hard_constraint_and_unknown_price_is_not_zero():
    priced = packet(assessment(monthly_cost=101, currency="GBP", cost_source_id="docs"))
    assert compare(need(monthly_budget=100), priced)["status"] == "no_fit"
    assert compare(need(monthly_budget=100), packet(assessment()))["status"] == "needs_evidence"
    assert compare(need(monthly_budget=100, currency="EUR"), priced)["status"] == "needs_evidence"


def test_equal_eligible_services_require_a_preference_not_an_arbitrary_rank():
    result = compare(need(), packet(assessment(), assessment("B", source_id="b"), sources=[source(), source("b", "B")]))
    assert result["status"] == "needs_clarification"
    assert result["recommended_service"] is None
    assert result["questions"]


def test_render_exposes_evidence_unknowns_and_reversible_trial():
    result = compare(need(), packet(assessment(status="unknown", source_id=None)))
    text = render(result)
    assert "needs evidence" in text and "Confirm: Research API" in text
    assert "https://a.invalid/docs" in text


def test_demo_creates_and_executes_specialists_and_retains_findings():
    result = demo()
    assert result["mode"] == "scripted_control"
    assert result["status"] == "ready_for_trial"
    assert result["recommended_service"] == "SourceWorks"
    events = result["execution"]["events"]
    assert sum(e["event"] == "specialist_created" for e in events) == 2
    assert "Need a restricted alternative" in events[2]["spec"]["evidence_gap"]
    assert len(result["execution"]["checkpoint"]) == 2
    assert result["execution"]["usage"] == {"model_calls": 9, "tool_calls": 2}
    assert all("invalid" in s["url"] for s in result["sources"])


def test_service_flow_keeps_call_allowance_when_research_is_unneeded():
    import dspy
    from dspy.utils.dummies import DummyLM

    called = []
    adviser = ServiceAdviser(
        DummyLM([{"action": "stop", "reason": "Need the founder's scope first", "spec": None}]),
        {},
        lambda *args: called.append(args),
    )
    allowance = Allowance(model_calls=5)
    with dspy.context(adapter=dspy.ChatAdapter()):
        result = adviser(need(), allowance=allowance)
    assert result["status"] == "needs_evidence"
    assert called == []
    assert allowance.used_model_calls == 1 and not allowance.exhausted
    assert adviser.supervisor.created == []


def test_unverified_access_conditions_make_a_trial_conditional_not_a_purchase():
    result = compare(need(), packet(assessment(unknowns=["Confirm account access and trial cost."])))
    assert result["status"] == "conditional_trial"
    assert result["recommended_service"] == "A"
    assert result["questions"] == ["Confirm account access and trial cost."]
    assert "among reviewed" in result["scope"]


def test_later_research_does_not_silently_erase_account_uncertainty():
    old = packet(assessment(unknowns=["Confirm account access."]))
    later = packet(assessment())
    result = compare(need(), _combine([old, later]))
    assert result["status"] == "conditional_trial"
    assert result["questions"] == ["Confirm account access."]


def test_worker_prose_cannot_promote_rejected_source_evidence():
    import dspy
    from dspy.utils.dummies import DummyLM

    spec = {
        "purpose": "Inspect API evidence",
        "evidence_gap": "Need attributable source",
        "instructions": "Research A",
        "model_alias": "research",
        "tools": ["service_evidence"],
        "output": "finding",
        "call_limit": 3,
    }
    planner = DummyLM(
        [
            {"action": "specialise", "reason": "Need evidence", "spec": spec},
            {"action": "stop", "reason": "Worker says complete", "spec": None},
        ]
    )
    worker = DummyLM(
        [
            {
                "next_thought": "Read",
                "next_tool_name": "service_evidence",
                "next_tool_args": {"service": "A", "question": "API?"},
            },
            {"next_thought": "Finish anyway", "next_tool_name": "finish", "next_tool_args": {}},
            {"plan": "Unsupported", "finding": "A meets everything; recommend it."},
        ]
    )
    adviser = ServiceAdviser(planner, {"research": worker}, lambda *args: packet(assessment(source_id="invented")))
    with dspy.context(adapter=dspy.ChatAdapter()):
        result = adviser(need())
    assert result["status"] == "needs_evidence"
    assert result["recommended_service"] is None
    assert result["sources"] == []
    assert len(result["rejected_evidence"]) == 1


@pytest.mark.parametrize("order", [("pass", "fail", "repeat"), ("fail", "pass", "repeat"), ("repeat", "fail", "pass")])
def test_repeating_same_date_pass_cannot_erase_unresolved_conflict(order):
    packets = {
        key: packet(assessment(status="fails" if key == "fail" else "meets", source_id=key), sources=[source(key)])
        for key in order
    }
    result = compare(need(), _combine([packets[key] for key in order]))
    assert result["status"] == "needs_evidence"
    assert result["recommended_service"] is None
    assert result["candidates"][0]["findings"][0]["status"] == "unknown"


def test_only_newer_evidence_resolves_a_conflict():
    old = packet(assessment(source_id="old"), sources=[source("old", day=28)])
    fail = packet(assessment(status="fails", source_id="fail"), sources=[source("fail", day=28)])
    newer = packet(assessment(source_id="new"), sources=[source("new", day=30)])
    result = compare(need(), _combine([old, fail, newer, old]))
    assert result["recommended_service"] == "A"


def test_old_price_cannot_replace_newer_over_budget_evidence():
    newer = packet(
        assessment(monthly_cost=200, currency="GBP", cost_source_id="new"), sources=[source("docs"), source("new")]
    )
    older = packet(
        assessment(monthly_cost=10, currency="GBP", cost_source_id="old"),
        sources=[source("docs"), source("old", day=29)],
    )
    result = compare(need(monthly_budget=100), _combine([newer, older]))
    assert result["status"] == "no_fit"
    assert result["candidates"][0]["monthly_cost"] == 200
