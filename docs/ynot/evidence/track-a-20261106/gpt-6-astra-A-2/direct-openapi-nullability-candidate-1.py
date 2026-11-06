from copy import deepcopy


def transform(payload):
    """Convert OpenAPI 3.0 nullability at schema positions only."""
    result = deepcopy(payload)

    def convert(schema):
        nullable = schema.pop("nullable", False)
        if nullable is True and "type" in schema:
            schema["type"] = [schema["type"], "null"]

        for child in schema.get("properties", {}).values():
            convert(child)

        if "items" in schema:
            convert(schema["items"])

        additional = schema.get("additionalProperties")
        if isinstance(additional, dict):
            convert(additional)

        for keyword in ("allOf", "anyOf", "oneOf"):
            for child in schema.get(keyword, []):
                convert(child)

        if "not" in schema:
            convert(schema["not"])

    convert(result)
    return result
