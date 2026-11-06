def transform(payload):
    import copy

    result = copy.deepcopy(payload)

    def visit(schema, parent_required=None, property_name=None):
        if not isinstance(schema, dict):
            return schema

        was_required = parent_required is None or property_name in parent_required
        original_type = schema.get("type")
        had_null_type = (
            original_type == "null"
            or isinstance(original_type, list) and "null" in original_type
        )

        schema.pop("default", None)

        if "properties" in schema:
            properties = schema["properties"]
            required = schema.get("required", [])
            if not isinstance(required, list):
                required = []
            original_required = set(required)
            schema["additionalProperties"] = False
            schema["required"] = sorted(properties.keys())
            for name, child in properties.items():
                visit(child, original_required, name)

        if "items" in schema:
            visit(schema["items"])

        if "anyOf" in schema:
            for branch in schema["anyOf"]:
                visit(branch)

        if property_name is not None and not was_required:
            if isinstance(original_type, str) and original_type != "null":
                schema["type"] = [original_type, "null"]
            elif isinstance(original_type, list) and not had_null_type:
                schema["type"] = original_type + ["null"]
            if isinstance(schema.get("enum"), list) and None not in schema["enum"]:
                schema["enum"] = schema["enum"] + [None]

        return schema

    return visit(result)
