def transform(payload):
    import copy

    result = copy.deepcopy(payload)

    def visit(schema, parent_required=None, property_name=None):
        if not isinstance(schema, dict):
            return

        was_optional = parent_required is not None and property_name not in parent_required
        schema.pop("default", None)

        if was_optional:
            value_type = schema.get("type")
            if isinstance(value_type, str) and value_type != "null":
                schema["type"] = [value_type, "null"]
            elif isinstance(value_type, list) and "null" not in value_type:
                schema["type"] = value_type + ["null"]
            enum = schema.get("enum")
            if isinstance(enum, list) and None not in enum:
                schema["enum"] = enum + [None]

        properties = schema.get("properties")
        if isinstance(properties, dict):
            original_required = schema.get("required", [])
            if not isinstance(original_required, list):
                original_required = []
            schema["additionalProperties"] = False
            schema["required"] = sorted(properties.keys())
            for name, child in properties.items():
                visit(child, original_required, name)

        if "items" in schema:
            visit(schema["items"])

        branches = schema.get("anyOf")
        if isinstance(branches, list):
            for branch in branches:
                visit(branch)

    visit(result)
    return result