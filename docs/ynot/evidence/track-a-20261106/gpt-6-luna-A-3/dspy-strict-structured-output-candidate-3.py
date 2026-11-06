def transform(payload):
    import copy

    result = copy.deepcopy(payload)

    def visit(schema, parent_required=None, property_name=None):
        if not isinstance(schema, dict):
            return

        schema.pop("default", None)

        if parent_required is not None and property_name not in parent_required:
            schema_type = schema.get("type")
            if isinstance(schema_type, str) and schema_type != "null":
                schema["type"] = [schema_type, "null"]
            elif isinstance(schema_type, list) and "null" not in schema_type:
                schema["type"] = schema_type + ["null"]

            enum = schema.get("enum")
            if isinstance(enum, list) and None not in enum:
                schema["enum"] = enum + [None]

        properties = schema.get("properties")
        if isinstance(properties, dict):
            original_required = schema.get("required", [])
            schema["additionalProperties"] = False
            schema["required"] = sorted(properties)
            for name, subschema in properties.items():
                visit(subschema, original_required, name)

        if "items" in schema:
            visit(schema["items"])

        branches = schema.get("anyOf")
        if isinstance(branches, list):
            for branch in branches:
                visit(branch)

    visit(result)
    return result