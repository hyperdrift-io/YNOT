"""Strict normalisation of the fleet's real MCP tool input schemas; the unseen tools are the holdouts.

Track A of docs/ynot/EVALUATION.md. Thirty-six tools on three Hyperdrift
servers define twenty-nine distinct input schemas, kept as the servers emit
them. Eight are host cases; the other twenty-one are reused on only after
acceptance. Expected outputs were derived
twice, by the control and by an independent reader of the specification, and
agreed on every tool.
"""

import json
from pathlib import Path

from examples.ynot import strict_schema_case
from ynot import AcceptanceCase, CapabilityContract

NAME = "mcp-tool-strict"
TASK = (
    "Make the fleet's MCP tool input schemas acceptable to a strict structured-output client "
    "and leave reusable Python code for the remaining tools."
)

SPECIFICATION = """
Implement transform(payload), returning a converted JSON Schema dictionary for a
client that enforces the strict structured-output subset. The input is the input
schema of an MCP tool as its server emits it: root type "object"; it may already
contain additionalProperties, $schema, pattern, length and numeric bounds,
defaults and descriptions. It uses no $ref, $defs, allOf, oneOf, not or
patternProperties, and every property schema has "type".
Rules:
1. Every schema that has "properties" sets "additionalProperties": false and
   "required" to all of its property names sorted by name (code point order),
   replacing any existing required list and any existing additionalProperties
   value. JSON object key order is not significant anywhere in the input or
   output.
2. A property that was not in its parent's original required list must accept
   null. If its "type" is a string other than "null", type becomes
   [original type, "null"]. If "type" is a list without "null", append "null".
   If the property has an "enum" without null, append null to the enum.
   A type that already includes "null" is unchanged.
3. Remove the "default" keyword from every schema.
4. Schemas in scope: the root, each value of "properties", "items" and each
   branch of "anyOf". Values of "enum", "default", "const", "examples" and x-*
   extensions are data, never schemas.
5. Preserve every other keyword, annotation and value, including description,
   title, format, $schema and the order of enum values.
Do not read files, use network access or print. Return finite JSON data only.
""".strip()

# The rules are the strict job's rules; the inputs are real.
CONTROL_SOURCE = strict_schema_case.CONTROL_SOURCE

FIXTURE = Path(__file__).with_name("cases") / "mcp-tool-schemas.json"
HOST_INDEXES = (0, 1, 4, 10, 12, 15, 19, 25)
SCOPE_KEYS = ("items", "not", "additionalProperties")
BRANCH_KEYS = ("anyOf", "allOf", "oneOf")


def tools():
    return json.loads(FIXTURE.read_text())["tools"]


def initial_observation():
    """The strict client's live rejection of one fleet tool schema, unchanged."""
    return json.loads((Path(__file__).with_name("cases") / "mcp-tool-strict-observation.json").read_text())


def contract():
    chosen = [tools()[index] for index in HOST_INDEXES]
    return CapabilityContract(
        NAME,
        "1",
        {"type": "object"},
        {"type": "object"},
        [AcceptanceCase(tool["payload"], tool["expected"]) for tool in chosen],
    )


def later_tools():
    return [tool for index, tool in enumerate(tools()) if index not in HOST_INDEXES]


def later_jobs():
    """The unseen tools, opened only after the candidate has been accepted."""
    return [AcceptanceCase(tool["payload"], tool["expected"]) for tool in later_tools()]


def strict_lint(schema, path="$"):
    """Does the output satisfy a strict client, whatever its wording? (ok, reason)."""
    if not isinstance(schema, dict):
        return True, "strict"
    for key in ("$ref", "nullable", "default"):
        if key in schema:
            return False, f"{path}: {key} present"
    if "properties" in schema:
        if schema.get("additionalProperties") is not False:
            return False, f"{path}: additionalProperties is not false"
        if schema.get("required") != sorted(schema["properties"]):
            return False, f"{path}: required does not list every property"
        for name, child in schema["properties"].items():
            ok, reason = strict_lint(child, f"{path}.{name}")
            if not ok:
                return ok, reason
    for key in SCOPE_KEYS:
        if isinstance(schema.get(key), dict):
            ok, reason = strict_lint(schema[key], f"{path}.{key}")
            if not ok:
                return ok, reason
    for key in BRANCH_KEYS:
        for index, branch in enumerate(schema.get(key) or []):
            ok, reason = strict_lint(branch, f"{path}.{key}[{index}]")
            if not ok:
                return ok, reason
    return True, "strict"


def behaviour(holdout_index, output):
    """Second measure on holdouts: strictness itself, independent of exact wording."""
    return strict_lint(output)
