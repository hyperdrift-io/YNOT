def transform(payload):
    import copy

    def convert(schema):
        if not isinstance(schema, dict):
            return copy.deepcopy(schema)

        result = {}
        for key, value in schema.items():
            if key == "nullable":
                continue
            if key == "properties" and isinstance(value, dict):
                result[key] = {name: convert(child) for name, child in value.items()}
            elif key in ("allOf", "anyOf", "oneOf") and isinstance(value, list):
                result[key] = [convert(child) for child in value]
            elif key in ("items", "not"):
                result[key] = convert(value)
            elif key == "additionalProperties" and isinstance(value, dict):
                result[key] = convert(value)
            else:
                result[key] = copy.deepcopy(value)

        if schema.get("nullable") is True and "type" in schema:
            original_type = schema["type"]
            if isinstance(original_type, str):
                result["type"] = [original_type, "null"]
            elif isinstance(original_type, list):
                result["type"] = [item for item in original_type if item != "null"] + ["null"]

        return result

    return convert(payload)