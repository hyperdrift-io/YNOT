"""Prepare an OpenAPI 3.0 schema for a strict client: nullability migration, then strict normalisation.

This job is solvable by composing the two earlier capabilities. It tests whether an
arm reuses accepted work or regenerates it. Host fixtures are never sent to the model.
"""

import json
from pathlib import Path

from examples.ynot import schema_case, strict_schema_case
from ynot import AcceptanceCase, CapabilityContract

NAME = "openapi-to-strict"
TASK = "Prepare OpenAPI 3.0 schemas for a strict structured-output client and leave reusable work for later schemas."
STEPS = (schema_case.NAME, strict_schema_case.NAME)

SPECIFICATION = (
    "Implement transform(payload) that prepares an OpenAPI 3.0 object schema for a\n"
    "strict structured-output client. The result must equal applying step 1 and\n"
    "then step 2 below to the input. The input is in scope for both steps: an object\n"
    'schema whose root has type "object", where every property schema has "type",\n'
    "and which uses no $ref, $defs, allOf, oneOf, not, patternProperties or\n"
    "additionalProperties.\n\n"
    "Step 1, OpenAPI nullability migration:\n" + schema_case.SPECIFICATION + "\n\n"
    "Step 2, strict structured-output normalisation, applied to the result of step 1:\n"
    + strict_schema_case.SPECIFICATION
    + "\n\n"
    "If your catalogue lists accepted capabilities that implement these steps, you\n"
    "may return a composition naming them in order instead of writing new code.\n"
    "Do not read files, use network access or print. Return finite JSON data only."
)

# The deterministic control composes the two earlier controls; it is never a live-model answer.
CONTROL_SOURCE = (
    schema_case.CONTROL_SOURCE.replace("def transform(payload):", "def _migrate(payload):")
    + strict_schema_case.CONTROL_SOURCE.replace("def transform(payload):", "def _strict(payload):")
    + "def transform(payload):\n    return _strict(_migrate(payload))\n"
)

CASES = Path(__file__).with_name("cases") / "openapi-to-strict-cases.json"
HOLDOUTS = Path(__file__).with_name("cases") / "openapi-to-strict-holdouts.json"


def initial_observation():
    """Both failures the earlier jobs recorded apply to one unchanged schema."""
    return {
        "nullability": schema_case.initial_observation(),
        "strict_client": strict_schema_case.initial_observation(),
    }


def contract():
    return CapabilityContract(
        NAME,
        "1",
        {"type": "object"},
        {"type": "object"},
        [AcceptanceCase(pair["payload"], pair["expected"]) for pair in json.loads(CASES.read_text())],
    )


def later_jobs():
    """Separately authored inputs, opened only after the candidate has been accepted."""
    return [AcceptanceCase(pair["payload"], pair["expected"]) for pair in json.loads(HOLDOUTS.read_text())]
