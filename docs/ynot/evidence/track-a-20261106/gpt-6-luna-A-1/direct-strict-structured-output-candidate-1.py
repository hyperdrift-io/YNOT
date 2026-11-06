def transform(payload):
    import copy

    result = copy.deepcopy(payload)

    def visit(schema, originally_required=None):
        if not isinstance(schema, dict):
            return

        # Only property schemas are made nullable when they were optional in
        # their parent's original required list.
        if originally_required is not None and schema.get("type") != "null":
            schema_type = schema.get("type")
            if isinstance(schema_type, str):
                schema["type"] = [schema_type, "null"]
            elif isinstance(schema_type, list) and "null" not in schema_type:
                schema["type"] = schema_type + ["null"]
            if "enum" in schema and isinstance(schema["enum"], list) and None not in schema["enum"]:
                schema["enum"].append(None)

        schema.pop("default", None)

        if "properties" in schema:
            properties = schema["properties"]
            original_required = schema.get("required", [])
            if not isinstance(original_required, list):
                original_required = []
            required_set = set(original_required)
            schema["additionalProperties"] = False
            schema["required"] = sorted(properties.keys())
            for name, child in properties.items():
                visit(child, name not in required_set)

        if "items" in schema:
            visit(schema["items"])

        if "anyOf" in schema:
            for branch in schema["anyOf"]:
                visit(branch)

    visit(result)
    return result