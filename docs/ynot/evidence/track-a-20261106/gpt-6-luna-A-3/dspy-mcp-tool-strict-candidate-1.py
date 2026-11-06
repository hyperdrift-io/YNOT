def transform(payload):
    import copy

    result = copy.deepcopy(payload)

    def visit(schema, parent_required=None, property_name=None):
        if not isinstance(schema, dict):
            return

        schema.pop("default", None)

        if "properties" in schema:
            properties = schema["properties"]
            original_required = schema.get("required", [])
            if not isinstance(original_required, list):
                original_required = []

            schema["additionalProperties"] = False
            schema["required"] = sorted(properties)

            for name, child in properties.items():
                visit(child)
                if name not in original_required and isinstance(child, dict):
                    child_type = child.get("type")
                    if isinstance(child_type, str):
                        if child_type != "null":
                            child["type"] = [child_type, "null"]
                    elif isinstance(child_type, list) and "null" not in child_type:
                        child["type"] = child_type + ["null"]

                    enum = child.get("enum")
                    if isinstance(enum, list) and None not in enum:
                        child["enum"] = enum + [None]

        if "items" in schema:
            visit(schema["items"])

        branches = schema.get("anyOf")
        if isinstance(branches, list):
            for branch in branches:
                visit(branch)

    visit(result)
    return result