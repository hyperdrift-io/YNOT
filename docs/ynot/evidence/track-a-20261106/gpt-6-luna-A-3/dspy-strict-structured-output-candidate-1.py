def transform(payload):
    import copy

    result = copy.deepcopy(payload)

    def visit(schema, parent_required=None, property_name=None):
        if not isinstance(schema, dict):
            return

        was_required = parent_required is None or property_name in parent_required

        schema.pop("default", None)

        original_type = schema.get("type")
        if parent_required is not None and not was_required:
            if isinstance(original_type, str) and original_type != "null":
                schema["type"] = [original_type, "null"]
            elif isinstance(original_type, list) and "null" not in original_type:
                schema["type"] = original_type + ["null"]

            enum = schema.get("enum")
            if isinstance(enum, list) and None not in enum:
                schema["enum"] = enum + [None]

        properties = schema.get("properties")
        if isinstance(properties, dict):
            original_required = schema.get("required", [])
            if not isinstance(original_required, list):
                original_required = []
            schema["additionalProperties"] = False
            schema["required"] = sorted(properties)
            for name, subschema in properties.items():
                visit(subschema, original_required, name)

        if "items" in schema:
            visit(schema["items"])

        any_of = schema.get("anyOf")
        if isinstance(any_of, list):
            for branch in any_of:
                visit(branch)

    visit(result)
    return result