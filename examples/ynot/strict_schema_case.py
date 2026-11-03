"""Bounded strict structured-output normalisation; host fixtures are never sent to the model.

This is the second consumer of the capability lifecycle. The repository's own
Codex adapter hand-writes this normalisation for research packets, and MCP tool
schemas need the same shape before a strict client accepts them.
"""

import json
from pathlib import Path

from ynot import AcceptanceCase, CapabilityContract

NAME = "strict-structured-output"
TASK = (
    "Make generated JSON Schemas acceptable to a strict structured-output client "
    "and leave reusable Python code for later schemas."
)

SPECIFICATION = """
Implement transform(payload), returning a converted JSON Schema dictionary for a
client that enforces the strict structured-output subset. The input is a JSON
Schema whose root has type "object". It uses no $ref, $defs, allOf, oneOf, not,
patternProperties or additionalProperties, and every property schema has "type".
Rules:
1. Every schema that has "properties" sets "additionalProperties": false and
   "required" to all of its property names sorted by name (code point order),
   replacing any existing required list. JSON object key order is not
   significant anywhere in the input or output.
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
   title, format and the order of enum values.
Do not read files, use network access or print. Return finite JSON data only.
""".strip()

# The deterministic control is implementation evidence, never a live-model answer.
CONTROL_SOURCE = """def transform(payload):
    import copy
    def convert(schema, optional=False):
        if not isinstance(schema, dict):
            return copy.deepcopy(schema)
        result = {k: copy.deepcopy(v) for k, v in schema.items() if k != "default"}
        if optional:
            kind = result.get("type")
            if isinstance(kind, str) and kind != "null":
                result["type"] = [kind, "null"]
            elif isinstance(kind, list) and "null" not in kind:
                result["type"] = kind + ["null"]
            if "enum" in result and None not in result["enum"]:
                result["enum"] = result["enum"] + [None]
        if "properties" in schema:
            required = schema.get("required", [])
            result["properties"] = {k: convert(v, k not in required) for k, v in schema["properties"].items()}
            result["required"] = sorted(schema["properties"])
            result["additionalProperties"] = False
        if "items" in schema:
            result["items"] = convert(schema["items"])
        if "anyOf" in schema:
            result["anyOf"] = [convert(v) for v in schema["anyOf"]]
        return result
    return convert(payload)
"""

HOLDOUTS = Path(__file__).with_name("cases") / "strict-structured-output-holdouts.json"


def initial_observation():
    """The failure a strict client reports for an ordinary generated schema."""
    return json.loads((Path(__file__).with_name("cases") / "strict-structured-output-observation.json").read_text())


def contract():
    pairs = [
        (
            {
                "type": "object",
                "properties": {"a": {"type": "string"}, "b": {"type": "integer"}},
                "required": ["b", "a"],
            },
            {
                "type": "object",
                "properties": {"a": {"type": "string"}, "b": {"type": "integer"}},
                "required": ["a", "b"],
                "additionalProperties": False,
            },
        ),
        (
            {"type": "object", "properties": {"name": {"type": "string", "description": "Display name"}}},
            {
                "type": "object",
                "properties": {"name": {"type": ["string", "null"], "description": "Display name"}},
                "required": ["name"],
                "additionalProperties": False,
            },
        ),
        (
            {"type": "object", "properties": {"state": {"type": "string", "enum": ["open", "closed"]}}, "required": []},
            {
                "type": "object",
                "properties": {"state": {"type": ["string", "null"], "enum": ["open", "closed", None]}},
                "required": ["state"],
                "additionalProperties": False,
            },
        ),
        (
            {
                "type": "object",
                "title": "Settings",
                "properties": {"limit": {"type": "integer", "default": 10, "minimum": 1}},
                "required": ["limit"],
            },
            {
                "type": "object",
                "title": "Settings",
                "properties": {"limit": {"type": "integer", "minimum": 1}},
                "required": ["limit"],
                "additionalProperties": False,
            },
        ),
        (
            {
                "type": "object",
                "properties": {
                    "owner": {
                        "type": "object",
                        "properties": {"id": {"type": "string", "format": "uuid"}, "note": {"type": "string"}},
                        "required": ["id"],
                    }
                },
                "required": ["owner"],
            },
            {
                "type": "object",
                "properties": {
                    "owner": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string", "format": "uuid"},
                            "note": {"type": ["string", "null"]},
                        },
                        "required": ["id", "note"],
                        "additionalProperties": False,
                    }
                },
                "required": ["owner"],
                "additionalProperties": False,
            },
        ),
        (
            {
                "type": "object",
                "properties": {
                    "rows": {
                        "type": "array",
                        "items": {"type": "object", "properties": {"count": {"type": "integer"}}, "required": []},
                    }
                },
                "required": ["rows"],
            },
            {
                "type": "object",
                "properties": {
                    "rows": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {"count": {"type": ["integer", "null"]}},
                            "required": ["count"],
                            "additionalProperties": False,
                        },
                    }
                },
                "required": ["rows"],
                "additionalProperties": False,
            },
        ),
        (
            {
                "type": "object",
                "properties": {
                    "k": {
                        "anyOf": [
                            {"type": "string", "default": "s"},
                            {"type": "object", "properties": {"n": {"type": "number"}}},
                        ]
                    }
                },
                "required": ["k"],
                "examples": [{"k": {"default": 1, "properties": 2}}],
            },
            {
                "type": "object",
                "properties": {
                    "k": {
                        "anyOf": [
                            {"type": "string"},
                            {
                                "type": "object",
                                "properties": {"n": {"type": ["number", "null"]}},
                                "required": ["n"],
                                "additionalProperties": False,
                            },
                        ]
                    }
                },
                "required": ["k"],
                "additionalProperties": False,
                "examples": [{"k": {"default": 1, "properties": 2}}],
            },
        ),
    ]
    return CapabilityContract(
        "strict-structured-output",
        "1",
        {"type": "object"},
        {"type": "object"},
        [AcceptanceCase(payload, expected) for payload, expected in pairs],
    )


def later_jobs():
    """Separately authored inputs, opened only after the candidate has been accepted."""
    return [AcceptanceCase(pair["payload"], pair["expected"]) for pair in json.loads(HOLDOUTS.read_text())]
