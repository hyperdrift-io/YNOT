def transform(payload):
    schema = payload
    schema_positions = ("properties", "items", "additionalProperties", "allOf", "anyOf", "oneOf", "not")

    def visit(node):
        if isinstance(node, list):
            return [visit(item) for item in node]
        if not isinstance(node, dict):
            return node

        result = {}
        for key, value in node.items():
            if key in schema_positions:
                if key == "properties" and isinstance(value, dict):
                    result[key] = {name: visit(child) for name, child in value.items()}
                elif key in ("allOf", "anyOf", "oneOf") and isinstance(value, list):
                    result[key] = [visit(child) for child in value]
                elif key == "additionalProperties" and isinstance(value, bool):
                    result[key] = value
                else:
                    result[key] = visit(value)
            else:
                result[key] = value

        if result.pop("nullable", False) is True and "type" in result:
            original_type = result["type"]
            if isinstance(original_type, str):
                result["type"] = [original_type, "null"]
            elif isinstance(original_type, list):
                result["type"] = [t for t in original_type if t != "null"] + ["null"]
        return result

    return visit(schema)