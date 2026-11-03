from copy import deepcopy


def transform(payload):
    """Convert OpenAPI 3.0 nullability at schema positions without mutating input."""
    result = deepcopy(payload)

    def visit(schema):
        if not isinstance(schema, dict):
            return

        nullable = schema.pop("nullable", False)
        if nullable is True and "type" in schema:
            schema["type"] = [schema["type"], "null"]

        for child in schema.get("properties", {}).values():
            visit(child)

        for keyword in ("items", "additionalProperties", "not"):
            if keyword in schema:
                visit(schema[keyword])

        for keyword in ("allOf", "anyOf", "oneOf"):
            for child in schema.get(keyword, []):
                visit(child)

    visit(result)
    return result
