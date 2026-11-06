def transform(payload):
    import copy

    result = copy.deepcopy(payload)

    def visit(schema):
        if isinstance(schema, bool):
            return schema
        if not isinstance(schema, dict):
            return schema

        nullable = schema.pop("nullable", False)
        schema_type = schema.get("type")
        if nullable is True and isinstance(schema_type, str):
            if schema_type != "null":
                schema["type"] = [schema_type, "null"]

        for key in ("properties",):
            value = schema.get(key)
            if isinstance(value, dict):
                for child in value.values():
                    visit(child)

        for key in ("items", "additionalProperties", "not"):
            value = schema.get(key)
            if isinstance(value, (dict, bool)):
                visit(value)

        for key in ("allOf", "anyOf", "oneOf"):
            value = schema.get(key)
            if isinstance(value, list):
                for child in value:
                    visit(child)

        return schema

    visit(result)
    return result