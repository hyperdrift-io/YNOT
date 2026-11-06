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
            elif key in ("items", "not", "additionalProperties") and isinstance(value, (dict, bool)):
                result[key] = convert(value)
            elif key in ("allOf", "anyOf", "oneOf") and isinstance(value, list):
                result[key] = [convert(child) for child in value]
            else:
                result[key] = value

        original = schema.get("type")
        if schema.get("nullable") is True and isinstance(original, (str, list)):
            types = [original] if isinstance(original, str) else [item for item in original if item != "null"]
            result["type"] = types + ["null"]

        return result

    return convert(payload)