"""Compatibility entry point and scripted control for the YNOT runtime.

Use ``from ynot import Supervisor, Allowance`` in new applications.
"""

import json

import dspy
from ynot.runtime import (  # noqa: F401 -- preserve existing example imports
    Allowance,
    CountedEngine,
    NextStep,
    RunLimitError,
    Supervisor,
    WorkerSpec,
)


def scripted_demo():
    from dspy.utils.dummies import DummyLM

    def source(query: str) -> str:
        """Read fictional public-source material for the controlled demonstration."""
        return "Example Works: example.invalid/jobs, dated 2026-10-01; needs a data-import workflow."

    def spec(purpose, gap, output="finding"):
        return {
            "purpose": purpose,
            "evidence_gap": gap,
            "instructions": f"{purpose}. Cite uncertainty.",
            "model_alias": "research",
            "tools": ["source"],
            "output": output,
            "call_limit": 3,
        }

    planner = DummyLM(
        [
            {"action": "specialise", "reason": "Need source evidence", "spec": spec("Check fit", "No evidence yet")},
            {
                "action": "specialise",
                "reason": "Assess the finding",
                "spec": spec("Challenge fit", "Need counterevidence", "opportunity"),
            },
            {"action": "stop", "reason": "Fictional opportunity ready for review, not a buyer claim", "spec": None},
        ]
    )
    research = DummyLM(
        [
            {"next_thought": "Read the source", "next_tool_name": "source", "next_tool_args": {"query": "import"}},
            {"next_thought": "Have evidence", "next_tool_name": "finish", "next_tool_args": {}},
            {"plan": "Source is fictional", "finding": "Example Works mentions data imports; budget unknown."},
            {"next_thought": "Assess retained finding", "next_tool_name": "finish", "next_tool_args": {}},
            {
                "plan": "No purchase evidence",
                "opportunity": "Illustrative fit only; confirm need and budget before pursuing.",
            },
        ]
    )
    supervisor = Supervisor(planner, {"research": research}, {"source": source})
    allowance = Allowance()
    with dspy.context(adapter=dspy.ChatAdapter()):
        result = supervisor("Find one customer worth pursuing for an integration consultancy.", allowance=allowance)
    return {
        "mode": "scripted_control",
        "usage": {"model_calls": allowance.used_model_calls, "tool_calls": allowance.used_tool_calls},
        **result.toDict(),
    }


if __name__ == "__main__":
    print(json.dumps(scripted_demo(), indent=2))
