"""Bounded OpenAPI nullability repair; host fixtures are never sent to the model."""

from jsonschema import Draft202012Validator

from ynot import AcceptanceCase, CapabilityContract

NAME = "openapi-nullability"
TASK = "Repair this API schema compatibility failure and leave reusable Python code for later schemas."

SPECIFICATION = """
Implement transform(payload), returning a converted schema dictionary. This is
only the nullability part of an OpenAPI 3.0 to 3.1 migration, not a full converter.
The input uses valid 3.0 schema keywords, without Reference Objects or $ref.
OpenAPI 3.0 nullable=true permits null only when type is explicitly present in
that same schema. Other constraints, including enum, continue to apply.
OpenAPI 3.1 uses JSON Schema types, including null. Remove the old nullable field
from schema positions. Preserve every other constraint, annotation and value.
For deterministic output, type arrays put the original type first and null last.
Nested schema positions in scope: properties, items, additionalProperties,
allOf, anyOf, oneOf, not. additionalProperties can also be a boolean.
Annotation data (example, default, enum, x-* extensions) is not a schema.
Do not read files, use network access or print. Return finite JSON data only.
""".strip()

# The deterministic control is implementation evidence, never a live-model answer.
CONTROL_SOURCE = """def transform(payload):
    import copy
    def convert(schema):
        if not isinstance(schema, dict):
            return copy.deepcopy(schema)
        result = copy.deepcopy(schema)
        nullable = result.pop("nullable", False)
        if nullable and isinstance(schema.get("type"), str):
            result["type"] = [schema["type"], "null"]
        if "properties" in schema:
            result["properties"] = {k: convert(v) for k, v in schema["properties"].items()}
        for key in ("items", "additionalProperties", "not"):
            if key in schema:
                result[key] = convert(schema[key])
        for key in ("allOf", "anyOf", "oneOf"):
            if key in schema:
                result[key] = [convert(v) for v in schema[key]]
        return result
    return convert(payload)
"""


def initial_observation():
    """The failure an actual JSON Schema validator reports for a 3.0 nullable schema."""
    schema = {"type": "string", "nullable": True, "description": "Optional display name"}
    errors = list(Draft202012Validator(schema).iter_errors(None))
    return {"schema": schema, "payload": None, "validator_error": errors[0].message}


def contract():
    pairs = [
        ({"type": "string", "nullable": True}, {"type": ["string", "null"]}),
        ({"type": "integer", "nullable": False}, {"type": "integer"}),
        ({"nullable": True, "enum": ["open"]}, {"enum": ["open"]}),
        (
            {"type": "string", "nullable": True, "enum": ["open", "closed"]},
            {"type": ["string", "null"], "enum": ["open", "closed"]},
        ),
        (
            {"type": "object", "properties": {"id": {"type": "integer", "nullable": True}}, "required": ["id"]},
            {"type": "object", "properties": {"id": {"type": ["integer", "null"]}}, "required": ["id"]},
        ),
        (
            {
                "type": "array",
                "items": {"type": "object", "additionalProperties": {"type": "number", "nullable": True}},
            },
            {"type": "array", "items": {"type": "object", "additionalProperties": {"type": ["number", "null"]}}},
        ),
        (
            {
                "allOf": [{"type": "object", "additionalProperties": False}],
                "example": {"nullable": True, "type": "string"},
            },
            {
                "allOf": [{"type": "object", "additionalProperties": False}],
                "example": {"nullable": True, "type": "string"},
            },
        ),
    ]
    return CapabilityContract(
        "openapi-nullability",
        "1",
        {"type": "object"},
        {"type": "object"},
        [AcceptanceCase(payload, expected) for payload, expected in pairs],
    )


def later_jobs():
    """Disjoint inputs, opened only after the candidate has been accepted."""
    return [
        AcceptanceCase(
            {
                "type": "object",
                "properties": {"aliases": {"type": "array", "nullable": True, "items": {"type": "string"}}},
            },
            {"type": "object", "properties": {"aliases": {"type": ["array", "null"], "items": {"type": "string"}}}},
        ),
        AcceptanceCase(
            {
                "anyOf": [{"type": "boolean", "nullable": True}, {"type": "integer"}],
                "default": {"nullable": True, "type": "number"},
            },
            {
                "anyOf": [{"type": ["boolean", "null"]}, {"type": "integer"}],
                "default": {"nullable": True, "type": "number"},
            },
        ),
        AcceptanceCase(
            {"not": {"type": "number", "nullable": True}, "x-sample": {"nullable": True, "type": "string"}},
            {"not": {"type": ["number", "null"]}, "x-sample": {"nullable": True, "type": "string"}},
        ),
        AcceptanceCase(
            {
                "oneOf": [
                    {"type": "string", "nullable": True, "enum": ["ok", None]},
                    {"type": "integer", "nullable": False},
                ]
            },
            {"oneOf": [{"type": ["string", "null"], "enum": ["ok", None]}, {"type": "integer"}]},
        ),
    ]
