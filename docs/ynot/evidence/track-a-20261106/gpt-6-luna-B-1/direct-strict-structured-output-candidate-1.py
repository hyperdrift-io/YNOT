def transform(payload):
    import copy

    result = copy.deepcopy(payload)

    def visit(schema, originally_required=None, is_property=False):
        if not isinstance(schema, dict):
            return

        schema.pop("default", None)

        if is_property and originally_required is False:
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
            schema["additionalProperties"] = False
            original_required_names = schema.get("required", [])
            if not isinstance(original_required_names, list):
                original_required_names = []
            required_set = set(original_required_names)
            schema["required"] = sorted(properties.keys())
            for name, child in properties.items():
                visit(child, name in required_set, True)

        items = schema.get("items")
        if isinstance(items, dict):
            visit(items)

        any_of = schema.get("anyOf")
        if isinstance(any_of, list):
            for branch in any_of:
                visit(branch)

    visit(result)
    return result