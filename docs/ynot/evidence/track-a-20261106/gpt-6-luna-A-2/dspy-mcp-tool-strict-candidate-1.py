def transform(payload):
    import copy

    result = copy.deepcopy(payload)

    def visit(schema, parent_required=None, property_name=None):
        if not isinstance(schema, dict):
            return

        was_optional = (
            parent_required is not None and property_name not in parent_required
        )

        schema.pop("default", None)

        if was_optional:
            schema_type = schema.get("type")
            if isinstance(schema_type, str):
                if schema_type != "null":
                    schema["type"] = [schema_type, "null"]
            elif isinstance(schema_type, list) and "null" not in schema_type:
                schema["type"] = schema_type + ["null"]

            enum = schema.get("enum")
            if isinstance(enum, list) and None not in enum:
                schema["enum"] = enum + [None]

        properties = schema.get("properties")
        if isinstance(properties, dict):
            original_required = schema.get("required", [])
            if not isinstance(original_required, list):
                original_required = []
            for name, child in properties.items():
                visit(child, original_required, name)
            schema["additionalProperties"] = False
            schema["required"] = sorted(properties)

        if "items" in schema:
            items = schema["items"]
            if isinstance(items, dict):
                visit(items)

        any_of = schema.get("anyOf")
        if isinstance(any_of, list):
            for branch in any_of:
                visit(branch)

    visit(result)
    return result