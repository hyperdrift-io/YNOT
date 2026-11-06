def transform(payload):
    import copy

    result = copy.deepcopy(payload)

    def visit(schema):
        schema.pop("default", None)

        properties = schema.get("properties")
        if properties is not None:
            original_required = schema.get("required", [])
            if not isinstance(original_required, list):
                original_required = []
            schema["additionalProperties"] = False
            schema["required"] = sorted(properties)

            for name, child in properties.items():
                was_required = name in original_required
                visit(child)
                if not was_required:
                    value = child["type"]
                    if isinstance(value, str):
                        if value != "null":
                            child["type"] = [value, "null"]
                    elif isinstance(value, list) and "null" not in value:
                        child["type"] = value + ["null"]
                    enum = child.get("enum")
                    if isinstance(enum, list) and None not in enum:
                        child["enum"] = enum + [None]

        if "items" in schema:
            visit(schema["items"])

        branches = schema.get("anyOf")
        if isinstance(branches, list):
            for branch in branches:
                visit(branch)

    visit(result)
    return result