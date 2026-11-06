def transform(payload):
    import copy

    result = copy.deepcopy(payload)

    def visit(schema, optional=False):
        if not isinstance(schema, dict):
            return

        schema.pop("default", None)

        if optional:
            typ = schema.get("type")
            if isinstance(typ, str):
                if typ != "null":
                    schema["type"] = [typ, "null"]
            elif isinstance(typ, list) and "null" not in typ:
                schema["type"] = typ + ["null"]

            enum = schema.get("enum")
            if isinstance(enum, list) and None not in enum:
                schema["enum"] = enum + [None]

        if "properties" in schema:
            properties = schema["properties"]
            original_required = schema.get("required", [])
            if not isinstance(original_required, list):
                original_required = []
            required_set = set(original_required)

            schema["additionalProperties"] = False
            schema["required"] = sorted(properties.keys())

            for name, child in properties.items():
                visit(child, optional=name not in required_set)

        if "items" in schema:
            visit(schema["items"])

        branches = schema.get("anyOf")
        if isinstance(branches, list):
            for branch in branches:
                visit(branch)

    visit(result)
    return result