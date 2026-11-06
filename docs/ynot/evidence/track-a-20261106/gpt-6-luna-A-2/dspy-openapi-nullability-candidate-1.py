def transform(payload):
    def convert(schema):
        if isinstance(schema, bool):
            return schema
        if not isinstance(schema, dict):
            return schema

        result = {}
        nullable = schema.get("nullable") is True
        explicit_type = "type" in schema and isinstance(schema["type"], (str, list))

        for key, value in schema.items():
            if key == "nullable":
                continue
            if key == "properties" and isinstance(value, dict):
                result[key] = {name: convert(child) for name, child in value.items()}
            elif key in ("items", "not") and isinstance(value, dict):
                result[key] = convert(value)
            elif key == "additionalProperties" and isinstance(value, dict):
                result[key] = convert(value)
            elif key in ("allOf", "anyOf", "oneOf") and isinstance(value, list):
                result[key] = [convert(child) for child in value]
            else:
                result[key] = value

        if nullable and explicit_type:
            original = schema["type"]
            if isinstance(original, str):
                result["type"] = [original, "null"]
            else:
                types = [item for item in original if item != "null"]
                result["type"] = types + ["null"]
        return result

    return convert(payload)