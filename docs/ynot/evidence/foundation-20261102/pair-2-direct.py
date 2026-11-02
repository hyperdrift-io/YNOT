from copy import deepcopy


def transform(payload):
    """Convert OpenAPI 3.0 nullability at schema positions only."""
    result = deepcopy(payload)

    def visit(schema):
        nullable = schema.pop("nullable", False)
        if nullable is True and "type" in schema:
            schema["type"] = [schema["type"], "null"]

        # Annotation data, including enum values, remains untouched.
        if "properties" in schema:
            for child in schema["properties"].values():
                visit(child)

        for keyword in ("items", "additionalProperties", "not"):
            child = schema.get(keyword)
            if isinstance(child, dict):
                visit(child)

        for keyword in ("allOf", "anyOf", "oneOf"):
            if keyword in schema:
                for child in schema[keyword]:
                    visit(child)

    visit(result)
    return result
