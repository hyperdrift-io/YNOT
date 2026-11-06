def transform(payload):
    import copy

    result = copy.deepcopy(payload)

    def visit(schema, originally_required=None):
        if not isinstance(schema, dict):
            return

        schema.pop("default", None)
        properties = schema.get("properties")
        if isinstance(properties, dict):
            original = schema.get("required", [])
            if not isinstance(original, list):
                original = []
            required = set(original)
            schema["additionalProperties"] = False
            schema["required"] = sorted(properties)

            for name, child in properties.items():
                visit(child, required)
                if name not in required and isinstance(child, dict):
                    typ = child.get("type")
                    if isinstance(typ, str) and typ != "null":
                        child["type"] = [typ, "null"]
                    elif isinstance(typ, list) and "null" not in typ:
                        child["type"] = typ + ["null"]
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