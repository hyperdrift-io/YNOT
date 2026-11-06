def transform(payload):
    import copy

    result = copy.deepcopy(payload)

    def visit(schema, originally_required=True):
        if not isinstance(schema, dict):
            return

        schema.pop("default", None)

        properties = schema.get("properties")
        if isinstance(properties, dict):
            original_required = schema.get("required", [])
            if not isinstance(original_required, list):
                original_required = []
            original_required = set(original_required)

            schema["additionalProperties"] = False
            schema["required"] = sorted(properties)

            for name, child in properties.items():
                visit(child, name in original_required)
                if name not in original_required and isinstance(child, dict):
                    typ = child.get("type")
                    if isinstance(typ, str):
                        if typ != "null":
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