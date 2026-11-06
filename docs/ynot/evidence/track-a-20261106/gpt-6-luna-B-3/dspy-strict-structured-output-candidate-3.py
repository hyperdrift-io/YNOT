def transform(payload):
    import copy

    result = copy.deepcopy(payload)

    def visit(schema, optional=False):
        schema.pop("default", None)

        if optional:
            schema_type = schema["type"]
            if isinstance(schema_type, str):
                if schema_type != "null":
                    schema["type"] = [schema_type, "null"]
            elif "null" not in schema_type:
                schema["type"] = schema_type + ["null"]

            enum = schema.get("enum")
            if isinstance(enum, list) and None not in enum:
                schema["enum"] = enum + [None]

        if "properties" in schema:
            properties = schema["properties"]
            original_required = set(schema.get("required", []))
            schema["additionalProperties"] = False
            schema["required"] = sorted(properties.keys())

            for name, child in properties.items():
                visit(child, name not in original_required)

        if "items" in schema:
            visit(schema["items"])

        for branch in schema.get("anyOf", []):
            visit(branch)

    visit(result)
    return result