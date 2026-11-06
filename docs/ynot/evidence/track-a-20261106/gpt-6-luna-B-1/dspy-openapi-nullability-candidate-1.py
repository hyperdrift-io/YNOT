def transform(payload):
    def convert(schema):
        if not isinstance(schema, dict):
            return schema

        result = {}
        for key, value in schema.items():
            if key in ("example", "default", "enum") or key.startswith("x-"):
                result[key] = value
            elif key == "nullable":
                continue
            elif key == "properties" and isinstance(value, dict):
                result[key] = {name: convert(child) for name, child in value.items()}
            elif key == "items":
                result[key] = convert(value)
            elif key == "additionalProperties":
                result[key] = convert(value) if isinstance(value, dict) else value
            elif key in ("allOf", "anyOf", "oneOf") and isinstance(value, list):
                result[key] = [convert(child) for child in value]
            elif key == "not":
                result[key] = convert(value)
            else:
                result[key] = value

        if schema.get("nullable") is True and "type" in schema:
            original_type = schema["type"]
            if isinstance(original_type, str):
                result["type"] = [original_type, "null"]
            elif isinstance(original_type, list) and "null" not in original_type:
                result["type"] = [*original_type, "null"]

        return result

    return convert(payload)