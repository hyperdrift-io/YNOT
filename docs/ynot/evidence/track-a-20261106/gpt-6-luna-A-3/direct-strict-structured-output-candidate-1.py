def transform(payload):
    import copy

    result = copy.deepcopy(payload)

    def visit(schema, parent_required=None, property_name=None):
        if not isinstance(schema, dict):
            return

        was_required = parent_required is None or property_name in parent_required

        # Transform children first, using this object's original required list.
        original_required = schema.get("required", [])
        if not isinstance(original_required, list):
            original_required = []

        properties = schema.get("properties")
        if isinstance(properties, dict):
            for name, child in properties.items():
                visit(child, original_required, name)
            schema["additionalProperties"] = False
            schema["required"] = sorted(properties.keys())

        items = schema.get("items")
        if isinstance(items, dict):
            visit(items)

        any_of = schema.get("anyOf")
        if isinstance(any_of, list):
            for branch in any_of:
                visit(branch)

        schema.pop("default", None)

        if property_name is not None and not was_required:
            typ = schema.get("type")
            if isinstance(typ, str):
                if typ != "null":
                    schema["type"] = [typ, "null"]
            elif isinstance(typ, list) and "null" not in typ:
                schema["type"] = typ + ["null"]

            enum = schema.get("enum")
            if isinstance(enum, list) and None not in enum:
                schema["enum"] = enum + [None]

    visit(result)
    return result