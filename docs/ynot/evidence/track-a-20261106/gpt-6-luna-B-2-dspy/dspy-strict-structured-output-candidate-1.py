def transform(payload):
    import copy

    result = copy.deepcopy(payload)

    def visit(schema, originally_required=True):
        if not isinstance(schema, dict):
            return

        schema.pop("default", None)

        if not originally_required:
            value_type = schema.get("type")
            if isinstance(value_type, str):
                if value_type != "null":
                    schema["type"] = [value_type, "null"]
            elif isinstance(value_type, list) and "null" not in value_type:
                schema["type"] = value_type + ["null"]

            enum = schema.get("enum")
            if isinstance(enum, list) and None not in enum:
                schema["enum"] = enum + [None]

        properties = schema.get("properties")
        if isinstance(properties, dict):
            required = set(schema.get("required", []))
            schema["additionalProperties"] = False
            schema["required"] = sorted(properties)
            for name, child in properties.items():
                visit(child, name in required)

        items = schema.get("items")
        if isinstance(items, dict):
            visit(items)

        any_of = schema.get("anyOf")
        if isinstance(any_of, list):
            for branch in any_of:
                visit(branch)

    visit(result)
    return result