def transform(payload):
    def convert(schema):
        if isinstance(schema, bool) or not isinstance(schema, dict):
            return schema

        result = {}
        for key, value in schema.items():
            if key == "nullable":
                continue
            if key == "properties" and isinstance(value, dict):
                result[key] = {name: convert(child) for name, child in value.items()}
            elif key in ("items", "not"):
                result[key] = convert(value)
            elif key == "additionalProperties" and isinstance(value, (dict, bool)):
                result[key] = convert(value)
            elif key in ("allOf", "anyOf", "oneOf") and isinstance(value, list):
                result[key] = [convert(child) for child in value]
            else:
                result[key] = value

        if schema.get("nullable") is True and "type" in schema:
            original_type = schema["type"]
            if isinstance(original_type, list):
                types = [item for item in original_type if item != "null"]
                result["type"] = types + ["null"]
            else:
                result["type"] = [original_type, "null"]

        return result

    return convert(payload)