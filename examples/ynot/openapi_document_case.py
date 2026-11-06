"""Prepare every component schema of a whole OpenAPI 3.0 document for a strict client.

Track A of docs/ynot/EVALUATION.md. Twenty-one public documents with
self-contained, acyclic component schemas: five are host cases, sixteen are
holdouts. The job needs traversal, in-document reference resolution and the
nullability and strict steps per component, so there are more places to be
wrong than in one bounded transform. Expected outputs were derived twice, by
the control and by an independent reader of the specification.
"""

import json
from pathlib import Path

from examples.ynot.mcp_tools_case import strict_lint
from ynot import AcceptanceCase, CapabilityContract

NAME = "openapi-components-strict"
TASK = (
    "Prepare every component schema of an OpenAPI 3.0 document for a strict structured-output client "
    "and leave reusable Python code for later documents."
)

SPECIFICATION = """
Implement transform(payload), where payload is a complete OpenAPI 3.0 document.
Return a dictionary mapping each name under components.schemas to that schema
prepared for a client that enforces the strict structured-output subset; the
result has exactly those names and nothing else. Prepare each component in
three stages, in this order.
Stage 1, resolve references. Every object whose "$ref" is a string of the form
"#/components/schemas/<name>" is replaced by a deep copy of the named component,
itself resolved the same way; any sibling keywords next to that "$ref" are
discarded. Documents in scope have no other reference forms and no reference
cycles.
Stage 2, nullability. OpenAPI 3.0 "nullable": true permits null only when "type"
is a string in the same schema: that type becomes [type, "null"]. Remove
"nullable" from every schema in scope whatever its value.
Stage 3, strict subset. Every schema that has "properties" sets
"additionalProperties": false and "required" to all of its property names sorted
by name (code point order), replacing any existing values. A property that was
not in its parent's original required list must accept null: if its "type" is a
string other than "null", type becomes [type, "null"]; if a list without "null",
append "null"; if it has an "enum" without null, append null; a type that
already includes "null" is unchanged. Remove "default" from every schema in
scope.
Schemas in scope, at every stage: the component root, each value of
"properties", "items", "additionalProperties" when it is an object, "not", and
each member of "allOf", "anyOf" and "oneOf". Values of "enum", "default",
"example", "examples", "const", "discriminator", "xml", "externalDocs" and x-*
extensions are data, never schemas.
Preserve every other keyword, annotation and value, including description,
title, format, example, xml, readOnly, deprecated and the order of enum values.
JSON object key order is not significant.
Do not read files, use network access or print. Return finite JSON data only.
""".strip()

# The deterministic control is implementation evidence, never a live-model answer.
CONTROL_SOURCE = """def transform(payload):
    import copy
    components = payload["components"]["schemas"]
    PREFIX = "#/components/schemas/"
    def resolve(schema):
        if not isinstance(schema, dict):
            return copy.deepcopy(schema)
        ref = schema.get("$ref")
        if isinstance(ref, str) and ref.startswith(PREFIX):
            return resolve(components[ref[len(PREFIX):]])
        out = {}
        for key, value in schema.items():
            if key == "properties" and isinstance(value, dict):
                out[key] = {k: resolve(v) for k, v in value.items()}
            elif key in ("items", "not") or (key == "additionalProperties" and isinstance(value, dict)):
                out[key] = resolve(value)
            elif key in ("allOf", "anyOf", "oneOf") and isinstance(value, list):
                out[key] = [resolve(v) for v in value]
            else:
                out[key] = copy.deepcopy(value)
        return out
    def nullability(schema):
        if not isinstance(schema, dict):
            return schema
        nullable = schema.pop("nullable", False)
        if nullable is True and isinstance(schema.get("type"), str):
            schema["type"] = [schema["type"], "null"]
        if isinstance(schema.get("properties"), dict):
            for v in schema["properties"].values():
                nullability(v)
        for key in ("items", "not"):
            if key in schema:
                nullability(schema[key])
        if isinstance(schema.get("additionalProperties"), dict):
            nullability(schema["additionalProperties"])
        for key in ("allOf", "anyOf", "oneOf"):
            if isinstance(schema.get(key), list):
                for v in schema[key]:
                    nullability(v)
        return schema
    def strict(schema, optional=False):
        if not isinstance(schema, dict):
            return schema
        result = {k: v for k, v in schema.items() if k != "default"}
        if optional:
            kind = result.get("type")
            if isinstance(kind, str) and kind != "null":
                result["type"] = [kind, "null"]
            elif isinstance(kind, list) and "null" not in kind:
                result["type"] = kind + ["null"]
            if "enum" in result and None not in result["enum"]:
                result["enum"] = result["enum"] + [None]
        if isinstance(schema.get("properties"), dict):
            required = schema.get("required") or []
            result["properties"] = {k: strict(v, k not in required) for k, v in schema["properties"].items()}
            result["required"] = sorted(schema["properties"])
            result["additionalProperties"] = False
        elif isinstance(schema.get("additionalProperties"), dict):
            result["additionalProperties"] = strict(schema["additionalProperties"])
        for key in ("items", "not"):
            if key in schema:
                result[key] = strict(schema[key])
        for key in ("allOf", "anyOf", "oneOf"):
            if isinstance(schema.get(key), list):
                result[key] = [strict(v) for v in schema[key]]
        return result
    return {name: strict(nullability(resolve(schema))) for name, schema in components.items()}
"""

FIXTURE = Path(__file__).with_name("cases") / "openapi-documents.json"
HOST_INDEXES = (0, 1, 2, 3, 15)


def documents():
    return json.loads(FIXTURE.read_text())["documents"]


def initial_observation():
    """The strict client's live rejection of an unprepared component."""
    return json.loads((Path(__file__).with_name("cases") / "openapi-components-observation.json").read_text())


def contract():
    chosen = [documents()[index] for index in HOST_INDEXES]
    return CapabilityContract(
        NAME,
        "1",
        {"type": "object"},
        {"type": "object"},
        [AcceptanceCase(doc["document"], doc["expected"]) for doc in chosen],
    )


def later_documents():
    return [doc for index, doc in enumerate(documents()) if index not in HOST_INDEXES]


def later_jobs():
    """The unseen documents, opened only after the candidate has been accepted."""
    return [AcceptanceCase(doc["document"], doc["expected"]) for doc in later_documents()]


def behaviour(holdout_index, output):
    """Every component strict, whatever the wording; the name set unchanged. (ok, reason)."""
    expected_names = set(later_documents()[holdout_index]["document"]["components"]["schemas"])
    if not isinstance(output, dict) or set(output) != expected_names:
        return False, "component names differ"
    for name, schema in output.items():
        ok, reason = strict_lint(schema, name)
        if not ok:
            return ok, reason
    return True, "strict"
