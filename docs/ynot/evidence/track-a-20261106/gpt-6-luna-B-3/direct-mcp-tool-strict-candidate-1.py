def transform(payload):
    import copy

    result = copy.deepcopy(payload)

    def visit(schema, parent_required=None, property_name=None):
        if not isinstance(schema, dict):
            return schema

        was_required = property_name is None or (
            isinstance(parent_required, list) and property_name in parent_required
        )

        schema.pop("default", None)

        properties = schema.get("properties")
        if isinstance(properties, dict):
            original_required = schema.get("required", [])
            schema["additionalProperties"] = False
            schema["required"] = sorted(properties.keys())
            for name, child in properties.items():
                visit(child, original_required, name)

        if "items" in schema:
            visit(schema["items"])

        branches = schema.get("anyOf")
        if isinstance(branches, list):
            for branch in branches:
                visit(branch)

        if property_name is not None and not was_required:
            typ = schema.get("type")
            if isinstance(typ, str) and typ != "null":
                schema["type"] = [typ, "null"]
            elif isinstance(typ, list) and "null" not in typ:
                schema["type"] = typ + ["null"]
            enum = schema.get("enum")
            if isinstance(enum, list) and None not in enum:
                schema["enum"] = enum + [None]

        return schema

    return visit(result)