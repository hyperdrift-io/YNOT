def transform(payload):
    import copy

    result = copy.deepcopy(payload)

    def visit(schema):
        if not isinstance(schema, dict):
            return

        schema.pop("default", None)

        if "properties" in schema:
            properties = schema["properties"]
            original_required = schema.get("required", [])
            for name, child in properties.items():
                if name not in original_required:
                    make_nullable(child)
                visit(child)
            schema["additionalProperties"] = False
            schema["required"] = sorted(properties)

        if "items" in schema:
            visit(schema["items"])

        if "anyOf" in schema:
            for branch in schema["anyOf"]:
                visit(branch)

    def make_nullable(schema):
        if not isinstance(schema, dict):
            return
        value = schema.get("type")
        if isinstance(value, str):
            if value != "null":
                schema["type"] = [value, "null"]
        elif isinstance(value, list) and "null" not in value:
            schema["type"] = value + ["null"]
        enum = schema.get("enum")
        if isinstance(enum, list) and None not in enum:
            schema["enum"] = enum + [None]

    visit(result)
    return result