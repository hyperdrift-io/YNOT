def transform(payload):
    import copy

    def convert(schema):
        if isinstance(schema, bool):
            return schema
        if not isinstance(schema, dict):
            return copy.deepcopy(schema)

        result = copy.deepcopy(schema)
        nullable = result.pop("nullable", False)
        schema_type = result.get("type")
        if nullable is True and isinstance(schema_type, str):
            result["type"] = [schema_type, "null"]

        for key in ("properties",):
            value = result.get(key)
            if isinstance(value, dict):
                result[key] = {name: convert(child) for name, child in value.items()}
        for key in ("items", "not"):
            if key in result:
                result[key] = convert(result[key])
        key = "additionalProperties"
        if key in result and isinstance(result[key], (dict, bool)):
            result[key] = convert(result[key])
        for key in ("allOf", "anyOf", "oneOf"):
            value = result.get(key)
            if isinstance(value, list):
                result[key] = [convert(child) for child in value]
        return result

    return convert(payload)
