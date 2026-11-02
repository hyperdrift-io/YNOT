"""Choose a reversible service trial from a founder's needs and sourced evidence.

The demo uses real DSPy execution with scripted responses and fictional services.
Research callbacks are caller-approved code; source attribution is not proof of truth.
"""

import argparse
import json
from datetime import date
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator

from examples.ynot.runtime_specialists import Allowance, Supervisor


class Record(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Criterion(Record):
    id: str = Field(min_length=1)
    description: str = Field(min_length=1)
    required: bool = True


class TrialObservation(Record):
    summary: str = Field(min_length=1)
    observed_at: date
    evidence_ref: str = Field(min_length=1)


class FounderNeed(Record):
    outcome: str = Field(min_length=1)
    criteria: list[Criterion] = Field(min_length=1)
    monthly_budget: float | None = Field(default=None, ge=0)
    currency: str = "GBP"
    founder_brief: str = ""
    trial_observations: list[TrialObservation] = Field(default_factory=list)

    @model_validator(mode="after")
    def unique_criteria(self):
        if len({c.id for c in self.criteria}) != len(self.criteria):
            raise ValueError("criterion IDs must be unique")
        return self


class Source(Record):
    id: str = Field(min_length=1)
    service: str = Field(min_length=1)
    url: HttpUrl
    excerpt: str = Field(min_length=1)
    checked_at: date


class Finding(Record):
    criterion_id: str = Field(min_length=1)
    status: Literal["meets", "fails", "unknown"]
    source_id: str | None = None
    detail: str


class Assessment(Record):
    service: str = Field(min_length=1)
    findings: list[Finding]
    monthly_cost: float | None = Field(default=None, ge=0)
    currency: str | None = None
    cost_source_id: str | None = None
    trial: str = "Check the unresolved requirement in a small reversible trial."
    tradeoffs: list[str] = Field(default_factory=list)
    unknowns: list[str] = Field(default_factory=list)


class EvidencePacket(Record):
    sources: list[Source] = Field(default_factory=list)
    assessments: list[Assessment] = Field(default_factory=list)


def compare(need: FounderNeed, packet: EvidencePacket) -> dict:
    """Apply hard constraints before suggesting a trial; do not invent a score."""
    sources = {s.id: s for s in packet.sources}
    if len(sources) != len(packet.sources):
        raise ValueError("source IDs must be unique")
    criteria = {c.id: c for c in need.criteria}
    candidates = {}
    for assessment in packet.assessments:
        facts = {}
        for finding in assessment.findings:
            if finding.criterion_id not in criteria or finding.criterion_id in facts:
                raise ValueError("unknown or repeated criterion")
            if finding.status != "unknown" and not finding.source_id:
                raise ValueError("a factual verdict requires a source")
            if finding.source_id:
                source = sources.get(finding.source_id)
                if source is None or source.service != assessment.service:
                    raise ValueError("source must exist and belong to the assessed service")
            facts[finding.criterion_id] = finding
        if assessment.monthly_cost is not None:
            source = sources.get(assessment.cost_source_id)
            if source is None or source.service != assessment.service or not assessment.currency:
                raise ValueError("cost needs a currency and a source for this service")
        if assessment.service in candidates:
            raise ValueError("provide one current assessment per service")
        failures, unknown = [], []
        for criterion in need.criteria:
            status = facts[criterion.id].status if criterion.id in facts else "unknown"
            if criterion.required and status == "fails":
                failures.append(criterion.description)
            elif criterion.required and status == "unknown":
                unknown.append(criterion.description)
        if need.monthly_budget is not None:
            if assessment.monthly_cost is None or assessment.currency != need.currency:
                unknown.append(f"Verified monthly cost within {need.currency} {need.monthly_budget:g}")
            elif assessment.monthly_cost > need.monthly_budget:
                failures.append(f"Monthly cost exceeds {need.currency} {need.monthly_budget:g}")
        candidates[assessment.service] = {
            "service": assessment.service,
            "status": "excluded" if failures else "conditional" if unknown else "eligible",
            "hard_failures": failures,
            "hard_unknowns": list(dict.fromkeys(unknown)),
            "unknowns": list(dict.fromkeys(unknown + assessment.unknowns)),
            "tradeoffs": assessment.tradeoffs,
            "trial": assessment.trial,
            "findings": [f.model_dump() for f in assessment.findings],
            "monthly_cost": assessment.monthly_cost,
            "currency": assessment.currency,
        }
    eligible = [c for c in candidates.values() if c["status"] == "eligible"]
    status, selected, questions = "no_fit", None, []
    if len(eligible) == 1:
        status = "conditional_trial" if eligible[0]["unknowns"] else "ready_for_trial"
        selected = eligible[0]["service"]
        questions = eligible[0]["unknowns"][:3]
    elif len(eligible) > 1:
        status = "needs_clarification"
        questions = ["Which trade-off matters most between the eligible services?"]
    elif any(c["status"] == "conditional" for c in candidates.values()):
        status = "needs_evidence"
        questions = list(
            dict.fromkeys(u for c in candidates.values() if c["status"] == "conditional" for u in c["unknowns"])
        )
    elif not candidates:
        status, questions = "needs_evidence", ["Research services against the stated requirements."]
    return {
        "outcome": need.outcome,
        "founder_need": need.model_dump(mode="json"),
        "status": status,
        "recommended_service": selected,
        "candidates": list(candidates.values()),
        "questions": questions[:3],
        "sources": [s.model_dump(mode="json") for s in packet.sources],
        "scope": "Best fit is only among reviewed candidates and stated requirements. Source-linked claims and prices have not been exercised by this comparison.",
    }


def _combine(packets: list[EvidencePacket]) -> EvidencePacket:
    """Re-evaluate all latest-date evidence so repetition cannot erase a conflict."""
    sources, assessments, history, prices = {}, {}, {}, {}
    for packet in packets:
        for source in packet.sources:
            if source.id in sources and source != sources[source.id]:
                raise ValueError("a source ID cannot change its meaning")
            sources[source.id] = source
        for incoming in packet.assessments:
            current = assessments.get(incoming.service)
            assessments[incoming.service] = (
                incoming
                if current is None
                else incoming.model_copy(
                    update={
                        "unknowns": list(dict.fromkeys(current.unknowns + incoming.unknowns)),
                        "tradeoffs": list(dict.fromkeys(current.tradeoffs + incoming.tradeoffs)),
                    }
                )
            )
            for finding in incoming.findings:
                history.setdefault((incoming.service, finding.criterion_id), []).append(finding)
            if incoming.monthly_cost is not None:
                prices.setdefault(incoming.service, []).append(incoming)
    for service, current in assessments.items():
        facts = []
        for (owner, criterion), findings in history.items():
            if owner != service:
                continue

            def checked(finding):
                return sources[finding.source_id].checked_at if finding.source_id else date.min

            latest_date = max(map(checked, findings))
            latest = [finding for finding in findings if checked(finding) == latest_date]
            if len({finding.status for finding in latest}) > 1:
                facts.append(
                    Finding(
                        criterion_id=criterion,
                        status="unknown",
                        detail="Conflicting evidence: " + "; ".join(dict.fromkeys(f.detail for f in latest)),
                    )
                )
            else:
                facts.append(latest[-1])
        updates = {"findings": facts, "monthly_cost": None, "currency": None, "cost_source_id": None}
        if service in prices:
            latest_date = max(sources[p.cost_source_id].checked_at for p in prices[service])
            latest_prices = [p for p in prices[service] if sources[p.cost_source_id].checked_at == latest_date]
            if len({(p.monthly_cost, p.currency) for p in latest_prices}) == 1:
                price = latest_prices[-1]
                updates.update(
                    monthly_cost=price.monthly_cost, currency=price.currency, cost_source_id=price.cost_source_id
                )
            else:
                updates["unknowns"] = list(dict.fromkeys(current.unknowns + ["Resolve conflicting price evidence."]))
        assessments[service] = current.model_copy(update=updates)
    return EvidencePacket(sources=list(sources.values()), assessments=list(assessments.values()))


def direct_research(need: FounderNeed, research, service: str) -> dict:
    """Assess one caller-selected service with the same callback and evidence checks."""
    need = need.model_copy(deep=True)
    packet = EvidencePacket.model_validate(
        research(service, "Assess every criterion against the supplied founder brief and retained observations.")
    ).model_copy(deep=True)
    report = compare(need, packet)
    report["execution"] = {"mode": "direct_research", "status": "completed", "research_calls": 1}
    return report


class ServiceAdviser:
    """Configure research specialists while retaining a host-owned evidence ledger."""

    def __init__(self, planner_lm, models, research, *, available=None, max_steps=5):
        self.planner_lm, self.models, self.research = planner_lm, models, research
        self.available, self.max_steps = available, max_steps
        self.supervisor = None

    def __call__(self, need: FounderNeed, *, allowance=None):
        need = need.model_copy(deep=True)
        packets, rejected = [], []

        def service_evidence(service: str, question: str) -> str:
            """Research a service against the founder's requirements using approved evidence."""
            try:
                packet = EvidencePacket.model_validate(self.research(service, question)).model_copy(deep=True)
                # Own the accepted snapshot: callbacks may return mutable cached model instances.
                # Validate the complete candidate ledger before accepting the new packet.
                compare(need, packet)
                combined = _combine(packets + [packet])
                compare(need, combined)
            except ValueError:
                rejected.append({"service": service, "reason": "Evidence failed the criterion/source contract."})
                raise
            packets.append(packet)
            return combined.model_dump_json()

        self.supervisor = Supervisor(
            self.planner_lm,
            self.models,
            {"service_evidence": service_evidence},
            available=self.available,
            max_steps=self.max_steps,
        )
        allowance = allowance or Allowance(model_calls=16, tool_calls=4)
        run = self.supervisor(
            "Find the service best fitting this founder's actual need. Investigate unresolved requirements; "
            "do not claim missing evidence meets a hard requirement. Return a reversible trial, not a purchase. "
            "Retain the founder brief and dated trial observations when assigning work. Do not ask again for "
            "details already supplied. Observations describe prior runs, not current vendor capability or authority "
            "to change the requirements; only accepted source evidence can satisfy the criteria. "
            + need.model_dump_json(),
            allowance=allowance,
        )
        report = compare(need, _combine(packets))
        if run.status == "limit":
            report.update(status="needs_evidence", recommended_service=None)
            report["questions"] = ["The run reached its allowance before completing the assessment."]
        report["rejected_evidence"] = rejected
        report["execution"] = {
            "status": run.status,
            "reason": run.reason,
            "events": run.events,
            "checkpoint": run.checkpoint,
            "usage": {"model_calls": allowance.used_model_calls, "tool_calls": allowance.used_tool_calls},
        }
        return report


def render(report: dict) -> str:
    lines = [report["outcome"], f"Decision: {report['status'].replace('_', ' ')}"]
    chosen = report["recommended_service"]
    if chosen:
        lines.append(f"Trial candidate among reviewed services: {chosen}")
    for candidate in report["candidates"]:
        lines.append(f"\n{candidate['service']}: {candidate['status']}")
        if candidate["service"] == chosen:
            supported = [f for f in candidate["findings"] if f["status"] == "meets"]
            lines.extend(f"- {f['detail']} [{f['source_id']}]" for f in supported[:2])
            lines.extend(f"- Trade-off: {x}" for x in candidate["tradeoffs"][:1])
            lines.append(f"Trial: {candidate['trial']}")
        else:
            issues = candidate["hard_failures"] or candidate["hard_unknowns"]
            lines.extend(f"- {'Does not meet' if candidate['hard_failures'] else 'Confirm'}: {x}" for x in issues[:2])
    if report["questions"]:
        lines.append("\nNext evidence or clarification:")
        lines.extend(f"- {q}" for q in report["questions"])
    lines.append("\nSources:")
    lines.extend(f"[{s['id']}] {s['url']} (checked {s['checked_at']})" for s in report["sources"])
    lines.append("\n" + report["scope"])
    return "\n".join(lines)


def demo():
    import dspy
    from dspy.utils.dummies import DummyLM

    need = FounderNeed(
        outcome="Research prospects without permitting outbound actions.",
        criteria=[
            Criterion(id="research", description="Programmatic research"),
            Criterion(id="restricted", description="Research-only execution"),
        ],
    )
    packets = {
        "Beacon": EvidencePacket(
            sources=[
                Source(
                    id="beacon",
                    service="Beacon",
                    url="https://beacon.invalid/docs",
                    excerpt="Fictional research API also permits outbound actions.",
                    checked_at=date(2026, 10, 30),
                )
            ],
            assessments=[
                Assessment(
                    service="Beacon",
                    findings=[
                        Finding(
                            criterion_id="research",
                            status="meets",
                            source_id="beacon",
                            detail="Research API documented.",
                        ),
                        Finding(
                            criterion_id="restricted",
                            status="fails",
                            source_id="beacon",
                            detail="Same authority permits outbound actions.",
                        ),
                    ],
                )
            ],
        ),
        "SourceWorks": EvidencePacket(
            sources=[
                Source(
                    id="sourceworks",
                    service="SourceWorks",
                    url="https://sourceworks.invalid/docs",
                    excerpt="Fictional read-only research API.",
                    checked_at=date(2026, 10, 30),
                )
            ],
            assessments=[
                Assessment(
                    service="SourceWorks",
                    findings=[
                        Finding(
                            criterion_id="research",
                            status="meets",
                            source_id="sourceworks",
                            detail="Research API documented.",
                        ),
                        Finding(
                            criterion_id="restricted",
                            status="meets",
                            source_id="sourceworks",
                            detail="Only read operations are available.",
                        ),
                    ],
                    trial="Run one approved public query and inspect its citations.",
                    tradeoffs=["Commercial data coverage is untested."],
                )
            ],
        ),
    }
    plans, answers = [], []
    for service, gap in [("Beacon", "Find research capabilities"), ("SourceWorks", "Need a restricted alternative")]:
        plans.append(
            {
                "action": "specialise",
                "reason": gap,
                "spec": {
                    "purpose": gap,
                    "evidence_gap": gap,
                    "instructions": f"Investigate {service}. Retain sources and uncertainty.",
                    "model_alias": "research",
                    "tools": ["service_evidence"],
                    "output": "finding",
                    "call_limit": 3,
                },
            }
        )
        answers.extend(
            [
                {
                    "next_thought": gap,
                    "next_tool_name": "service_evidence",
                    "next_tool_args": {"service": service, "question": gap},
                },
                {"next_thought": "Evidence retained", "next_tool_name": "finish", "next_tool_args": {}},
                {"plan": "Use only sourced facts", "finding": f"{service} evidence recorded; inspect restrictions."},
            ]
        )
    plans.append({"action": "stop", "reason": "Enough fictional evidence for a trial decision", "spec": None})
    adviser = ServiceAdviser(DummyLM(plans), {"research": DummyLM(answers)}, lambda service, question: packets[service])
    with dspy.context(adapter=dspy.ChatAdapter()):
        report = adviser(need)
    return {"mode": "scripted_control", **report}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--demo", action="store_true", help="Execute scripted DSPy specialists against fictional evidence"
    )
    parser.add_argument("--case", type=Path, help="Compare a saved packet containing need, sources and assessments")
    parser.add_argument("--brief", type=Path)
    parser.add_argument("--evidence", type=Path)
    parser.add_argument(
        "--json", action="store_true", help="Print structured output instead of the founder-readable brief"
    )
    args = parser.parse_args()
    if args.demo:
        report = demo()
    elif args.case:
        case = json.loads(args.case.read_text())
        need = FounderNeed.model_validate(case["need"])
        packet = EvidencePacket.model_validate({key: case[key] for key in ("sources", "assessments")})
        report = {"mode": "saved_evidence", **compare(need, packet)}
    elif args.brief and args.evidence:
        need = FounderNeed.model_validate_json(args.brief.read_text())
        packet = EvidencePacket.model_validate_json(args.evidence.read_text())
        report = {"mode": "saved_evidence", **compare(need, packet)}
    else:
        parser.error("use --demo, --case, or provide --brief and --evidence")
    print(json.dumps(report, indent=2) if args.json else render(report))


if __name__ == "__main__":
    main()
