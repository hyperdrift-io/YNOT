def transform(payload):
    import copy

    result = copy.deepcopy(payload)

    def visit(schema, original_required=None):
        if not isinstance(schema, dict):
            return

        was_required = set(original_required or ())

        schema.pop("default", None)

        properties = schema.get("properties")
        if isinstance(properties, dict):
            schema["additionalProperties"] = False
            schema["required"] = sorted(properties)

            for name, child in properties.items():
                visit(child)
                if name not in was_required and isinstance(child, dict):
                    child_type = child.get("type")
                    if isinstance(child_type, str):
                        if child_type != "null":
                            child["type"] = [child_type, "null"]
                    elif isinstance(child_type, list) and "null" not in child_type:
                        child["type"] = child_type + ["null"]

                    enum = child.get("enum")
                    if isinstance(enum, list) and None not in enum:
                        child["enum"] = enum + [None]

        items = schema.get("items")
        if isinstance(items, dict):
            visit(items)

        any_of = schema.get("anyOf")
        if isinstance(any_of, list):
            for branch in any_of:
                visit(branch)

    visit(result, payload.get("required", []))
    return result