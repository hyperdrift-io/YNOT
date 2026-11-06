def transform(payload):
    import copy

    result = copy.deepcopy(payload)

    def visit(schema, parent_required=None, property_name=None):
        if not isinstance(schema, dict):
            return

        original_required = set(schema.get("required", []))
        has_properties = "properties" in schema
        properties = schema.get("properties")

        if has_properties and isinstance(properties, dict):
            schema["additionalProperties"] = False
            schema["required"] = sorted(properties)
            for name, child in properties.items():
                was_required = name in original_required
                visit(child, was_required, name)
                if not was_required and isinstance(child, dict):
                    child_type = child.get("type")
                    if isinstance(child_type, str) and child_type != "null":
                        child["type"] = [child_type, "null"]
                    elif isinstance(child_type, list) and "null" not in child_type:
                        child["type"] = child_type + ["null"]
                    enum = child.get("enum")
                    if isinstance(enum, list) and None not in enum:
                        child["enum"] = enum + [None]

        schema.pop("default", None)

        if "items" in schema:
            visit(schema["items"])

        any_of = schema.get("anyOf")
        if isinstance(any_of, list):
            for branch in any_of:
                visit(branch)

    visit(result)
    return result