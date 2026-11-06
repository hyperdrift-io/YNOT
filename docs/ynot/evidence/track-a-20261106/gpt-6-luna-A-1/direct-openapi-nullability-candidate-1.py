def transform(payload):
    """Convert OpenAPI 3.0 nullable schemas to OpenAPI 3.1 null types."""
    schema_positions = {
        "properties": "map",
        "items": "schema",
        "additionalProperties": "schema_or_bool",
        "allOf": "list",
        "anyOf": "list",
        "oneOf": "list",
        "not": "schema",
    }

    def visit(schema):
        if not isinstance(schema, dict):
            return schema

        result = dict(schema)
        nullable = result.pop("nullable", False)
        original_type = result.get("type")
        if nullable is True and isinstance(original_type, str):
            result["type"] = [original_type, "null"]
        elif nullable is True and isinstance(original_type, list):
            types = [t for t in original_type if t != "null"]
            result["type"] = types + ["null"]

        for key, kind in schema_positions.items():
            value = result.get(key)
            if kind == "map" and isinstance(value, dict):
                result[key] = {name: visit(child) for name, child in value.items()}
            elif kind == "schema" and isinstance(value, dict):
                result[key] = visit(value)
            elif kind == "schema_or_bool" and isinstance(value, dict):
                result[key] = visit(value)
            elif kind == "list" and isinstance(value, list):
                result[key] = [visit(child) for child in value]
        return result

    return visit(payload)
