def transform(payload):
    root = payload.get("schema") if isinstance(payload, dict) and "schema" in payload else payload

    def visit_schema(schema):
        if not isinstance(schema, dict):
            return schema

        result = dict(schema)
        nullable = schema.get("nullable") is True
        schema_type = schema.get("type")
        result.pop("nullable", None)

        if nullable and isinstance(schema_type, str):
            result["type"] = [schema_type, "null"]
        elif nullable and isinstance(schema_type, list):
            types = [item for item in schema_type if item != "null"]
            result["type"] = types + ["null"]

        properties = schema.get("properties")
        if isinstance(properties, dict):
            result["properties"] = {
                name: visit_schema(child) for name, child in properties.items()
            }

        for keyword in ("items", "additionalProperties", "not"):
            child = schema.get(keyword)
            if isinstance(child, dict):
                result[keyword] = visit_schema(child)

        for keyword in ("allOf", "anyOf", "oneOf"):
            children = schema.get(keyword)
            if isinstance(children, list):
                result[keyword] = [visit_schema(child) for child in children]

        return result

    return visit_schema(root)