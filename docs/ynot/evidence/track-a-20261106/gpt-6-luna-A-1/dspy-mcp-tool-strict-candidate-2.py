def transform(payload):
    import copy

    result = copy.deepcopy(payload)

    def visit(schema):
        if not isinstance(schema, dict):
            return

        schema.pop("default", None)
        original_required = schema.get("required", [])
        if not isinstance(original_required, list):
            original_required = []

        properties = schema.get("properties")
        if isinstance(properties, dict):
            schema["additionalProperties"] = False
            schema["required"] = sorted(properties)

            for name, prop_schema in properties.items():
                if not isinstance(prop_schema, dict):
                    continue

                if name not in original_required:
                    prop_type = prop_schema.get("type")
                    if isinstance(prop_type, str) and prop_type != "null":
                        prop_schema["type"] = [prop_type, "null"]
                    elif isinstance(prop_type, list) and "null" not in prop_type:
                        prop_schema["type"] = prop_type + ["null"]

                    enum = prop_schema.get("enum")
                    if isinstance(enum, list) and None not in enum:
                        prop_schema["enum"] = enum + [None]

                visit(prop_schema)

        if "items" in schema:
            visit(schema["items"])

        any_of = schema.get("anyOf")
        if isinstance(any_of, list):
            for branch in any_of:
                visit(branch)

    visit(result)
    return result