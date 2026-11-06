def transform(payload):
    import copy

    def convert(schema):
        if isinstance(schema, bool):
            return schema
        if not isinstance(schema, dict):
            return copy.deepcopy(schema)

        result = copy.deepcopy(schema)
        nullable = result.pop("nullable", False)
        original_type = result.get("type")
        if nullable is True and isinstance(original_type, str):
            result["type"] = [original_type, "null"]

        for key in ("properties",):
            mapping = result.get(key)
            if isinstance(mapping, dict):
                result[key] = {name: convert(child) for name, child in mapping.items()}

        for key in ("items", "additionalProperties", "not"):
            child = result.get(key)
            if isinstance(child, (dict, bool)):
                result[key] = convert(child)

        for key in ("allOf", "anyOf", "oneOf"):
            children = result.get(key)
            if isinstance(children, list):
                result[key] = [convert(child) for child in children]

        return result

    return convert(payload)
