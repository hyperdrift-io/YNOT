def transform(payload):
    import copy

    result = copy.deepcopy(payload)

    def visit(schema, optional=False):
        if not isinstance(schema, dict):
            return

        original_required = schema.get("required", [])
        properties = schema.get("properties")

        if isinstance(properties, dict):
            schema["additionalProperties"] = False
            schema["required"] = sorted(properties)
            for name, child in properties.items():
                visit(child, name not in original_required)

        if "items" in schema:
            visit(schema["items"])

        branches = schema.get("anyOf")
        if isinstance(branches, list):
            for branch in branches:
                visit(branch)

        schema.pop("default", None)

        if optional:
            schema_type = schema.get("type")
            if isinstance(schema_type, str) and schema_type != "null":
                schema["type"] = [schema_type, "null"]
            elif isinstance(schema_type, list) and "null" not in schema_type:
                schema["type"] = schema_type + ["null"]

            enum = schema.get("enum")
            if isinstance(enum, list) and None not in enum:
                schema["enum"] = enum + [None]

    visit(result)
    return result