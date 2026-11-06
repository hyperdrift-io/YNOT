def transform(payload):
    import copy

    result = copy.deepcopy(payload)

    def visit(schema, parent_required=None, property_name=None):
        if not isinstance(schema, dict):
            return

        was_required = parent_required is None or property_name in parent_required
        schema.pop("default", None)

        if not was_required:
            schema_type = schema.get("type")
            if isinstance(schema_type, str):
                if schema_type != "null":
                    schema["type"] = [schema_type, "null"]
            elif isinstance(schema_type, list) and "null" not in schema_type:
                schema_type.append("null")

            enum = schema.get("enum")
            if isinstance(enum, list) and None not in enum:
                enum.append(None)

        properties = schema.get("properties")
        if isinstance(properties, dict):
            original_required = schema.get("required", [])
            if not isinstance(original_required, list):
                original_required = []
            schema["additionalProperties"] = False
            schema["required"] = sorted(properties.keys())
            for name, child in properties.items():
                visit(child, original_required, name)

        items = schema.get("items")
        if isinstance(items, dict):
            visit(items)

        any_of = schema.get("anyOf")
        if isinstance(any_of, list):
            for branch in any_of:
                visit(branch)

    visit(result)
    return result