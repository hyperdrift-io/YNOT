def transform(payload):
    import copy

    result = copy.deepcopy(payload)

    def walk(schema):
        if not isinstance(schema, dict):
            return

        schema.pop("default", None)

        properties = schema.get("properties")
        if isinstance(properties, dict):
            original_required = schema.get("required", [])
            if not isinstance(original_required, list):
                original_required = []
            was_required = set(original_required)

            for name, prop_schema in properties.items():
                if isinstance(prop_schema, dict):
                    if name not in was_required:
                        typ = prop_schema.get("type")
                        if isinstance(typ, str) and typ != "null":
                            prop_schema["type"] = [typ, "null"]
                        elif isinstance(typ, list) and "null" not in typ:
                            prop_schema["type"] = typ + ["null"]
                        enum = prop_schema.get("enum")
                        if isinstance(enum, list) and None not in enum:
                            prop_schema["enum"] = enum + [None]
                    walk(prop_schema)

            schema["required"] = sorted(properties.keys())
            schema["additionalProperties"] = False

        items = schema.get("items")
        if isinstance(items, dict):
            walk(items)
        elif isinstance(items, list):
            for item_schema in items:
                walk(item_schema)

        any_of = schema.get("anyOf")
        if isinstance(any_of, list):
            for branch in any_of:
                walk(branch)

    walk(result)
    return result