def transform(payload):
    import copy

    result = copy.deepcopy(payload)

    def visit(schema, parent_required=None, name=None):
        if not isinstance(schema, dict):
            return

        was_optional = (
            parent_required is not None
            and name not in parent_required
        )

        schema.pop("default", None)

        if was_optional:
            schema_type = schema.get("type")
            if isinstance(schema_type, str):
                if schema_type != "null":
                    schema["type"] = [schema_type, "null"]
            elif isinstance(schema_type, list) and "null" not in schema_type:
                schema_type = list(schema_type)
                schema_type.append("null")
                schema["type"] = schema_type

            enum = schema.get("enum")
            if isinstance(enum, list) and None not in enum:
                schema["enum"] = enum + [None]

        if "properties" in schema:
            properties = schema["properties"]
            original_required = schema.get("required", [])
            if not isinstance(original_required, list):
                original_required = []
            schema["additionalProperties"] = False
            schema["required"] = sorted(properties)
            for property_name, property_schema in properties.items():
                visit(property_schema, original_required, property_name)

        if "items" in schema:
            visit(schema["items"])

        any_of = schema.get("anyOf")
        if isinstance(any_of, list):
            for branch in any_of:
                visit(branch)

    visit(result)
    return result