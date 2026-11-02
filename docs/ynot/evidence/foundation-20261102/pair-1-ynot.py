from copy import deepcopy


def transform(payload):
    """Convert OpenAPI 3.0 nullability without altering other constraints."""
    def convert(schema):
        result = {}
        for key, value in schema.items():
            if key == "nullable":
                continue
            if key == "properties":
                result[key] = {
                    name: convert(child) for name, child in value.items()
                }
            elif key in ("items", "not"):
                result[key] = convert(value)
            elif key == "additionalProperties":
                result[key] = value if isinstance(value, bool) else convert(value)
            elif key in ("allOf", "anyOf", "oneOf"):
                result[key] = [convert(child) for child in value]
            else:
                # Annotation and extension contents are data, not schemas.
                result[key] = deepcopy(value)

        if schema.get("nullable") is True and "type" in schema:
            result["type"] = [schema["type"], "null"]
        return result

    return convert(payload)
