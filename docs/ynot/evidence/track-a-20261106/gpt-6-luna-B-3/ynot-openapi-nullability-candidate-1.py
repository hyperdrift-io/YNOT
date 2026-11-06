def transform(payload):
    def visit(value):
        if isinstance(value, list):
            return [visit(item) for item in value]
        if not isinstance(value, dict):
            return value

        result = {key: visit(child) for key, child in value.items()}
        nullable = value.get("nullable") is True
        schema_type = value.get("type")
        if nullable and isinstance(schema_type, (str, list)):
            if isinstance(schema_type, str):
                result["type"] = [schema_type, "null"]
            else:
                types = list(schema_type)
                if "null" not in types:
                    types.append("null")
                result["type"] = types
        result.pop("nullable", None)
        return result

    schema = payload.get("schema") if isinstance(payload, dict) and "schema" in payload else payload
    return visit(schema)