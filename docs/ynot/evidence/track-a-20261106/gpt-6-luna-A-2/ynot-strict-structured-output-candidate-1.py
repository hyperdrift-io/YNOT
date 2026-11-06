def transform(payload):
    import copy

    result = copy.deepcopy(payload)

    def visit(schema, parent_required=None, property_name=None):
        if not isinstance(schema, dict):
            return

        was_optional = parent_required is not None and property_name not in parent_required

        schema.pop("default", None)

        if was_optional:
            typ = schema.get("type")
            if isinstance(typ, str) and typ != "null":
                schema["type"] = [typ, "null"]
            elif isinstance(typ, list) and "null" not in typ:
                schema["type"] = typ + ["null"]
            enum = schema.get("enum")
            if isinstance(enum, list) and None not in enum:
                schema["enum"] = enum + [None]

        if "properties" in schema:
            props = schema["properties"]
            original_required = schema.get("required", [])
            if not isinstance(original_required, list):
                original_required = []
            schema["additionalProperties"] = False
            schema["required"] = sorted(props.keys())
            for name, child in props.items():
                visit(child, original_required, name)

        if "items" in schema:
            visit(schema["items"])

        branches = schema.get("anyOf")
        if isinstance(branches, list):
            for branch in branches:
                visit(branch)

    visit(result)
    return result