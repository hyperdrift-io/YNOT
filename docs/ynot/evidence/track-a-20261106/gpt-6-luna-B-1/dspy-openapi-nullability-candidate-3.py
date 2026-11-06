def transform(payload):
    def convert(schema):
        if not isinstance(schema, dict):
            return schema

        nullable = schema.get("nullable") is True and "type" in schema
        original_type = schema.get("type")
        result = {}

        for key, value in schema.items():
            if key == "nullable":
                continue
            if key == "properties" and isinstance(value, dict):
                result[key] = {name: convert(child) for name, child in value.items()}
            elif key in ("items", "not"):
                result[key] = convert(value)
            elif key == "additionalProperties" and isinstance(value, dict):
                result[key] = convert(value)
            elif key in ("allOf", "anyOf", "oneOf") and isinstance(value, list):
                result[key] = [convert(child) for child in value]
            else:
                result[key] = value

        if nullable:
            if isinstance(original_type, str):
                result["type"] = [original_type, "null"]
            elif isinstance(original_type, list) and "null" not in original_type:
                result["type"] = [*original_type, "null"]

        return result

    return convert(payload)