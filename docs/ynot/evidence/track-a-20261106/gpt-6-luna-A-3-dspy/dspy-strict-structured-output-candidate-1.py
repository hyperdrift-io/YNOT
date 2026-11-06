def transform(payload):
    import copy

    result = copy.deepcopy(payload)

    def visit(schema, originally_required=True):
        if not isinstance(schema, dict):
            return

        schema.pop("default", None)

        properties = schema.get("properties")
        if isinstance(properties, dict):
            required_before = schema.get("required", [])
            required_before = set(required_before) if isinstance(required_before, list) else set()
            schema["additionalProperties"] = False
            schema["required"] = sorted(properties)

            for name, child in properties.items():
                visit(child, name in required_before)
                if name not in required_before and isinstance(child, dict):
                    value = child.get("type")
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