"""Draft-04 to 2020-12 migration over the official test suite; verdicts must survive.

Track A of docs/ynot/EVALUATION.md. The 146 usable draft-04 groups of
json-schema-org/JSON-Schema-Test-Suite are the population: ten are host cases,
136 are holdouts. Each group carries instance documents with their draft-04
verdicts, so a holdout has two measures: exact match with the expected
document, and behaviour, meaning the output validates as 2020-12 and gives every
instance the same verdict. Fifteen groups are excluded and listed in the
fixture: remote references, and reference semantics that changed between the
drafts. Expected outputs were derived twice and agreed on every group.
"""

import json
from pathlib import Path

from jsonschema import Draft202012Validator, exceptions

from examples.ynot import migration_case
from ynot import AcceptanceCase, CapabilityContract

NAME = "draft04-suite-migration"
TASK = (
    "Migrate the official JSON Schema draft-04 test-suite schemas to draft 2020-12 so they validate "
    "and keep every instance verdict, and leave reusable Python code for the remaining schemas."
)
SPECIFICATION = migration_case.SPECIFICATION
CONTROL_SOURCE = migration_case.CONTROL_SOURCE

FIXTURE = Path(__file__).with_name("cases") / "draft04-suite.json"
HOST_INDEXES = tuple(range(0, 146, 15))


def groups():
    return json.loads(FIXTURE.read_text())["groups"]


def initial_observation():
    """The current validator's rejection of an unchanged suite schema."""
    group = next(g for g in groups() if g["file"] == "items" and isinstance(g["schema"].get("items"), list))
    try:
        Draft202012Validator.check_schema(group["schema"])
    except exceptions.SchemaError as error:
        return {
            "schema": group["schema"],
            "validator": "jsonschema Draft202012Validator.check_schema",
            "error": error.message,
        }
    raise RuntimeError("Expected the 2020-12 meta-schema to reject a list-valued items")


def contract():
    chosen = [groups()[index] for index in HOST_INDEXES]
    return CapabilityContract(
        NAME,
        "1",
        {"type": "object"},
        {"type": "object"},
        [AcceptanceCase(group["schema"], group["expected"]) for group in chosen],
    )


def later_groups():
    return [group for index, group in enumerate(groups()) if index not in HOST_INDEXES]


def later_jobs():
    """The unseen groups, opened only after the candidate has been accepted."""
    return [AcceptanceCase(group["schema"], group["expected"]) for group in later_groups()]


def behaviour(holdout_index, output):
    """Does the output validate as 2020-12 and keep every instance verdict? (ok, reason)."""
    group = later_groups()[holdout_index]
    try:
        Draft202012Validator.check_schema(output)
        validator = Draft202012Validator(output)
        changed = [test["description"] for test in group["tests"] if validator.is_valid(test["data"]) != test["valid"]]
    except Exception as exc:
        return False, f"{type(exc).__name__}: {str(exc)[:120]}"
    if changed:
        return False, "verdict changed: " + "; ".join(changed[:3])
    return True, "behaviour preserved"
