def transform(payload):
    import copy

    result = copy.deepcopy(payload)

    def visit(schema):
        if not isinstance(schema, dict):
            return

        schema.pop("default", None)

        properties = schema.get("properties")
        if isinstance(properties, dict):
            original_required = set(schema.get("required", []))
            schema["additionalProperties"] = False
            schema["required"] = sorted(properties)

            for name, child in properties.items():
                was_required = name in original_required
                visit(child)

                if not was_required and isinstance(child, dict):
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