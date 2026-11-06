def transform(payload):
    import copy

    result = copy.deepcopy(payload)

    def visit(schema, originally_required=True):
        if not isinstance(schema, dict):
            return

        schema.pop("default", None)

        if not originally_required:
            schema_type = schema.get("type")
            if isinstance(schema_type, str):
                if schema_type != "null":
                    schema["type"] = [schema_type, "null"]
            elif isinstance(schema_type, list) and "null" not in schema_type:
                schema["type"] = schema_type + ["null"]

            enum = schema.get("enum")
            if isinstance(enum, list) and None not in enum:
                enum.append(None)

        properties = schema.get("properties")
        if isinstance(properties, dict):
            original_required = schema.get("required", [])
            if not isinstance(original_required, list):
                original_required = []
            required_set = set(original_required)
            schema["additionalProperties"] = False
            schema["required"] = sorted(properties)
            for name, child in properties.items():
                visit(child, name in required_set)

        if "items" in schema:
            visit(schema["items"])

        any_of = schema.get("anyOf")
        if isinstance(any_of, list):
            for branch in any_of:
                visit(branch)

    visit(result)
    return result