"""Bounded JSON Schema draft-04 to 2020-12 migration; host fixtures are never sent to the model.

Several renamed, retyped and split keywords interact, so a first candidate is
less likely to pass than the earlier single-rule jobs. The rules follow the
public release notes for draft-06, 2019-09 and 2020-12.
"""

import json
from pathlib import Path

from jsonschema import Draft202012Validator, exceptions

from ynot import AcceptanceCase, CapabilityContract

NAME = "schema-draft-migration"
TASK = "Migrate JSON Schema draft-04 documents to draft 2020-12 and leave reusable Python code for later documents."

SPECIFICATION = """
Implement transform(payload), returning the given JSON Schema draft-04 document
migrated to draft 2020-12. Rules:
1. Set "$schema" at the root to "https://json-schema.org/draft/2020-12/schema",
   replacing any existing value. Rename "id" to "$id" in every schema.
2. Rename "definitions" to "$defs" in every schema. Rewrite every "$ref" string
   value that starts with "#/definitions/" so it starts with "#/$defs/".
3. Where "exclusiveMinimum" is true and "minimum" is present, set
   "exclusiveMinimum" to the value of "minimum" and remove "minimum". Where it
   is false, or true without "minimum", remove it. Apply the same to
   "exclusiveMaximum" and "maximum". Numeric values are left unchanged.
4. Where "items" is a list of schemas, rename it to "prefixItems", then rename
   "additionalItems" to "items" if present. Where "items" is a single schema or
   absent, "items" is unchanged and "additionalItems" is removed.
5. Split "dependencies": entries whose value is a list of strings go under
   "dependentRequired"; entries whose value is a schema go under
   "dependentSchemas". Remove "dependencies". Omit either new keyword when it
   would have no entries.
6. Schemas in scope: the root; the values of "properties", "patternProperties",
   "definitions" and schema-valued "dependencies"; "items" (single or each list
   member), "additionalItems", "additionalProperties" when it is an object,
   "not"; and each member of "allOf", "anyOf" and "oneOf". Values of "enum",
   "const", "default", "examples" and x-* extensions are data, never schemas.
7. Preserve every other keyword, annotation and value. JSON object key order is
   not significant.
Do not read files, use network access or print. Return finite JSON data only.
""".strip()

SCHEMA_2020 = "https://json-schema.org/draft/2020-12/schema"

# The deterministic control is implementation evidence, never a live-model answer.
CONTROL_SOURCE = """def transform(payload):
    import copy
    SCHEMA = "https://json-schema.org/draft/2020-12/schema"
    def fix_ref(value):
        if isinstance(value, str) and value.startswith("#/definitions/"):
            return "#/$defs/" + value[len("#/definitions/"):]
        return value
    def convert(schema):
        if not isinstance(schema, dict):
            return copy.deepcopy(schema)
        out = {}
        for key, value in schema.items():
            if key == "id":
                out["$id"] = copy.deepcopy(value)
            elif key == "$ref":
                out["$ref"] = fix_ref(value)
            elif key == "definitions":
                out["$defs"] = {k: convert(v) for k, v in value.items()}
            elif key in ("properties", "patternProperties"):
                out[key] = {k: convert(v) for k, v in value.items()}
            elif key == "items":
                if isinstance(value, list):
                    out["prefixItems"] = [convert(v) for v in value]
                else:
                    out["items"] = convert(value)
            elif key == "additionalItems":
                if isinstance(schema.get("items"), list):
                    out["items"] = convert(value)
            elif key == "additionalProperties":
                out[key] = convert(value) if isinstance(value, dict) else copy.deepcopy(value)
            elif key == "not":
                out[key] = convert(value)
            elif key in ("allOf", "anyOf", "oneOf"):
                out[key] = [convert(v) for v in value]
            elif key == "dependencies":
                required = {k: copy.deepcopy(v) for k, v in value.items() if isinstance(v, list)}
                schemas = {k: convert(v) for k, v in value.items() if not isinstance(v, list)}
                if required:
                    out["dependentRequired"] = required
                if schemas:
                    out["dependentSchemas"] = schemas
            elif key in ("exclusiveMinimum", "exclusiveMaximum"):
                bound = "minimum" if key == "exclusiveMinimum" else "maximum"
                if isinstance(value, bool):
                    if value and bound in schema:
                        out[key] = copy.deepcopy(schema[bound])
                else:
                    out[key] = copy.deepcopy(value)
            elif key in ("minimum", "maximum"):
                exclusive = "exclusiveMinimum" if key == "minimum" else "exclusiveMaximum"
                if schema.get(exclusive) is not True:
                    out[key] = copy.deepcopy(value)
            else:
                out[key] = copy.deepcopy(value)
        return out
    result = convert(payload)
    result["$schema"] = SCHEMA
    return result
"""

HOLDOUTS = Path(__file__).with_name("cases") / "schema-draft-migration-holdouts.json"


def initial_observation():
    """The failure the current validator reports for an unchanged draft-04 schema."""
    schema = {
        "$schema": "http://json-schema.org/draft-04/schema#",
        "type": "number",
        "minimum": 0,
        "exclusiveMinimum": True,
    }
    try:
        Draft202012Validator.check_schema(schema)
    except exceptions.SchemaError as error:
        return {"schema": schema, "validator": "jsonschema Draft202012Validator.check_schema", "error": error.message}
    raise RuntimeError("Expected the 2020-12 meta-schema to reject a boolean exclusiveMinimum")


def contract():
    pairs = [
        (
            {"$schema": "http://json-schema.org/draft-04/schema#", "id": "https://example.com/a", "type": "string"},
            {"$schema": SCHEMA_2020, "$id": "https://example.com/a", "type": "string"},
        ),
        (
            {
                "definitions": {"name": {"type": "string"}},
                "properties": {"n": {"$ref": "#/definitions/name"}, "other": {"$ref": "#/components/x"}},
            },
            {
                "$schema": SCHEMA_2020,
                "$defs": {"name": {"type": "string"}},
                "properties": {"n": {"$ref": "#/$defs/name"}, "other": {"$ref": "#/components/x"}},
            },
        ),
        (
            {
                "properties": {
                    "a": {"type": "number", "minimum": 0, "exclusiveMinimum": True},
                    "b": {"type": "number", "maximum": 10, "exclusiveMaximum": False},
                    "c": {"type": "integer", "exclusiveMinimum": 3},
                    "d": {"type": "number", "exclusiveMaximum": True},
                }
            },
            {
                "$schema": SCHEMA_2020,
                "properties": {
                    "a": {"type": "number", "exclusiveMinimum": 0},
                    "b": {"type": "number", "maximum": 10},
                    "c": {"type": "integer", "exclusiveMinimum": 3},
                    "d": {"type": "number"},
                },
            },
        ),
        (
            {
                "type": "array",
                "items": [{"type": "string"}, {"type": "integer"}],
                "additionalItems": {"type": "boolean"},
            },
            {
                "$schema": SCHEMA_2020,
                "type": "array",
                "prefixItems": [{"type": "string"}, {"type": "integer"}],
                "items": {"type": "boolean"},
            },
        ),
        (
            {"type": "array", "items": {"type": "string", "id": "item"}, "additionalItems": False},
            {"$schema": SCHEMA_2020, "type": "array", "items": {"type": "string", "$id": "item"}},
        ),
        (
            {
                "type": "object",
                "dependencies": {
                    "card": ["cvv"],
                    "bank": {"properties": {"iban": {"type": "string"}}, "required": ["iban"]},
                },
            },
            {
                "$schema": SCHEMA_2020,
                "type": "object",
                "dependentRequired": {"card": ["cvv"]},
                "dependentSchemas": {"bank": {"properties": {"iban": {"type": "string"}}, "required": ["iban"]}},
            },
        ),
        (
            {
                "allOf": [{"not": {"enum": [{"id": 1, "definitions": {}}]}}, {"default": {"items": [1, 2]}}],
                "x-vendor": {"id": "keep", "$ref": "#/definitions/keep"},
            },
            {
                "$schema": SCHEMA_2020,
                "allOf": [{"not": {"enum": [{"id": 1, "definitions": {}}]}}, {"default": {"items": [1, 2]}}],
                "x-vendor": {"id": "keep", "$ref": "#/definitions/keep"},
            },
        ),
    ]
    return CapabilityContract(
        NAME, "1", {"type": "object"}, {"type": "object"}, [AcceptanceCase(p, e) for p, e in pairs]
    )


def later_jobs():
    """Separately authored inputs, opened only after the candidate has been accepted."""
    return [AcceptanceCase(pair["payload"], pair["expected"]) for pair in json.loads(HOLDOUTS.read_text())]
