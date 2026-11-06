def transform(payload):
    import copy

    result = copy.deepcopy(payload)

    def visit(schema, parent_required=None):
        if not isinstance(schema, dict):
            return

        was_required = set(parent_required or ())
        properties = schema.get("properties")

        # A property is optional according to the original parent schema, before
        # the parent's required list is replaced.
        if isinstance(properties, dict):
            original_required = schema.get("required", [])
            required_set = set(original_required) if isinstance(original_required, list) else set()
            for name, child in properties.items():
                visit(child)
                if name not in required_set and isinstance(child, dict):
                    child_type = child.get("type")
                    if isinstance(child_type, str) and child_type != "null":
                        child["type"] = [child_type, "null"]
                    elif isinstance(child_type, list) and "null" not in child_type:
                        child["type"] = child_type + ["null"]
                    enum = child.get("enum")
                    if isinstance(enum, list) and None not in enum:
                        child["enum"] = enum + [None]
            schema["additionalProperties"] = False
            schema["required"] = sorted(properties.keys())

        if "default" in schema:
            del schema["default"]

        if "items" in schema:
            visit(schema["items"])

        any_of = schema.get("anyOf")
        if isinstance(any_of, list):
            for branch in any_of:
                visit(branch)

    visit(result)
    return result