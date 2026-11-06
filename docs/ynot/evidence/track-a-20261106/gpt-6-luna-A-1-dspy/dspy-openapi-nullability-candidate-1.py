def transform(payload):
    import copy

    def convert(schema):
        if isinstance(schema, bool):
            return schema
        if not isinstance(schema, dict):
            return schema

        result = copy.deepcopy(schema)
        nullable = result.pop("nullable", False)
        original_type = result.get("type")

        if nullable is True and isinstance(original_type, str):
            result["type"] = [original_type, "null"]

        for key in ("properties",):
            value = result.get(key)
            if isinstance(value, dict):
                result[key] = {name: convert(child) for name, child in value.items()}

        for key in ("items", "additionalProperties", "not"):
            value = result.get(key)
            if isinstance(value, (dict, bool)):
                result[key] = convert(value)

        for key in ("allOf", "anyOf", "oneOf"):
            value = result.get(key)
            if isinstance(value, list):
                result[key] = [convert(child) for child in value]

        return result

    return convert(payload)