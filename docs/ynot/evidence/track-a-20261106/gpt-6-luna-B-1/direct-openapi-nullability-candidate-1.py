def transform(payload):
    def visit(schema):
        if isinstance(schema, bool):
            return schema
        if not isinstance(schema, dict):
            return schema

        result = {}
        for key, value in schema.items():
            if key == "nullable":
                continue
            if key == "properties" and isinstance(value, dict):
                result[key] = {name: visit(child) for name, child in value.items()}
            elif key == "items":
                if isinstance(value, list):
                    result[key] = [visit(child) for child in value]
                else:
                    result[key] = visit(value)
            elif key == "additionalProperties":
                result[key] = visit(value) if isinstance(value, dict) else value
            elif key in ("allOf", "anyOf", "oneOf") and isinstance(value, list):
                result[key] = [visit(child) for child in value]
            elif key == "not":
                result[key] = visit(value)
            else:
                result[key] = value

        if schema.get("nullable") is True and "type" in schema:
            original_type = schema["type"]
            if isinstance(original_type, str):
                result["type"] = [original_type, "null"]
            elif isinstance(original_type, list):
                result["type"] = [item for item in original_type if item != "null"] + ["null"]
        return result

    return visit(payload)