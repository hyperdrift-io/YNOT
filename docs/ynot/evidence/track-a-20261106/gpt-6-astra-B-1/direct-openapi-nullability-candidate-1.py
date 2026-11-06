from copy import deepcopy


def transform(payload):
    """Convert only OpenAPI 3.0 schema nullability to OpenAPI 3.1."""
    def convert(schema):
        result = deepcopy(schema)
        result.pop("nullable", None)

        # Nullability requires a type in this exact schema. Keep enum and
        # all other constraints intact, so they can still exclude null.
        if schema.get("nullable") is True and "type" in schema:
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
            result["additionalProperties"] = convert(
                schema["additionalProperties"]
            )

        for keyword in ("allOf", "anyOf", "oneOf"):
            if keyword in schema:
                result[keyword] = [convert(child) for child in schema[keyword]]

        # Annotation values and extension data are copied without conversion.
        return result

    return convert(payload)
