def transform(payload):
    import copy

    result = copy.deepcopy(payload)

    def visit(schema, parent_required=None):
        if not isinstance(schema, dict):
            return

        schema.pop("default", None)
        properties = schema.get("properties")

        if isinstance(properties, dict):
            original_required = schema.get("required", [])
            if not isinstance(original_required, list):
                original_required = []
            was_required = set(original_required)
            schema["additionalProperties"] = False
            schema["required"] = sorted(properties)

            for name, prop_schema in properties.items():
                if name not in was_required and isinstance(prop_schema, dict):
                    prop_type = prop_schema.get("type")
                    if isinstance(prop_type, str):
                        if prop_type != "null":
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