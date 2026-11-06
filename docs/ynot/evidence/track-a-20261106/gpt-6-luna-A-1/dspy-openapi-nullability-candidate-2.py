def transform(payload):
    """Convert OpenAPI 3.0 nullable schemas to OpenAPI 3.1 JSON Schema types."""
    import copy

    result = copy.deepcopy(payload)

    def convert(schema):
        if not isinstance(schema, dict):
            return

        nullable = schema.pop("nullable", False)
        schema_type = schema.get("type")
        if nullable is True and isinstance(schema_type, str):
            schema["type"] = [schema_type, "null"]

        properties = schema.get("properties")
        if isinstance(properties, dict):
            for child in properties.values():
                convert(child)

        for key in ("items", "additionalProperties", "not"):
            child = schema.get(key)
            if isinstance(child, dict):
                convert(child)

        for key in ("allOf", "anyOf", "oneOf"):
            children = schema.get(key)
            if isinstance(children, list):
                for child in children:
                    convert(child)

    convert(result)
    return result