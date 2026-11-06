def transform(payload):
    import copy

    result = copy.deepcopy(payload)

    def visit(schema, originally_required=True):
        if not isinstance(schema, dict):
            return

        schema.pop("default", None)

        properties = schema.get("properties")
        if isinstance(properties, dict):
            required = schema.get("required", [])
            required_set = set(required) if isinstance(required, list) else set()

            for name, child in properties.items():
                visit(child, name in required_set)
                if name not in required_set and isinstance(child, dict):
                    value_type = child.get("type")
                    if isinstance(value_type, str):
                        if value_type != "null":
                            child["type"] = [value_type, "null"]
                    elif isinstance(value_type, list) and "null" not in value_type:
                        child["type"] = value_type + ["null"]

                    enum = child.get("enum")
                    if isinstance(enum, list) and None not in enum:
                        child["enum"] = enum + [None]

            schema["additionalProperties"] = False
            schema["required"] = sorted(properties.keys())

        items = schema.get("items")
        if isinstance(items, dict):
            visit(items)

        any_of = schema.get("anyOf")
        if isinstance(any_of, list):
            for branch in any_of:
                visit(branch)

    visit(result)
    return result