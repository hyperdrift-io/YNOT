from copy import deepcopy


def transform(payload):
    """Convert OpenAPI 3.0 schema nullability to OpenAPI 3.1."""
    def convert(schema):
        result = deepcopy(schema)
        nullable = result.pop("nullable", False)
        if nullable is True and "type" in schema:
            result["type"] = [schema["type"], "null"]

        if "properties" in schema:
            result["properties"] = {
                name: convert(child)
                for name, child in schema["properties"].items()
            }

        for keyword in ("items", "not"):
            if keyword in schema:
                result[keyword] = convert(schema[keyword])

        if isinstance(schema.get("additionalProperties"), dict):
            result["additionalProperties"] = convert(schema["additionalProperties"])

        for keyword in ("allOf", "anyOf", "oneOf"):
            if keyword in schema:
                result[keyword] = [convert(child) for child in schema[keyword]]

        return result

    return convert(payload)
