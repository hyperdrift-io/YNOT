def transform(payload):
    import copy

    result = copy.deepcopy(payload)

    def visit(schema):
        if not isinstance(schema, dict):
            return

        schema.pop("default", None)
        original_required = schema.get("required", [])
        properties = schema.get("properties")
        if isinstance(properties, dict):
            schema["additionalProperties"] = False
            schema["required"] = sorted(properties)
            for name, child in properties.items():
                if name not in original_required:
                    child_type = child.get("type")
                    if isinstance(child_type, str) and child_type != "null":
                        child["type"] = [child_type, "null"]
                    elif isinstance(child_type, list) and "null" not in child_type:
                        child["type"] = child_type + ["null"]
                    enum = child.get("enum")
                    if isinstance(enum, list) and None not in enum:
                        child["enum"] = enum + [None]
                visit(child)

        items = schema.get("items")
        if isinstance(items, dict):
            visit(items)

        any_of = schema.get("anyOf")
        if isinstance(any_of, list):
            for branch in any_of:
                visit(branch)

    visit(result)
    return result