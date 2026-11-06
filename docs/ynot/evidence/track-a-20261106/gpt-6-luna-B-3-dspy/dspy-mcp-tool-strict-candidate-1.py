def transform(payload):
    import copy

    result = copy.deepcopy(payload)

    def visit(schema, originally_required=False):
        if not isinstance(schema, dict):
            return schema

        schema.pop("default", None)

        properties = schema.get("properties")
        if isinstance(properties, dict):
            original_required = schema.get("required", [])
            if not isinstance(original_required, list):
                original_required = []
            schema["additionalProperties"] = False
            schema["required"] = sorted(properties)
            for name, child in properties.items():
                was_required = name in original_required
                if isinstance(child, dict):
                    visit(child)
                    if not was_required:
                        child_type = child.get("type")
                        if isinstance(child_type, str) and child_type != "null":
                            child["type"] = [child_type, "null"]
                        elif isinstance(child_type, list) and "null" not in child_type:
                            child["type"] = child_type + ["null"]
                        enum = child.get("enum")
                        if isinstance(enum, list) and None not in enum:
                            child["enum"] = enum + [None]

        if "items" in schema:
            items = schema["items"]
            if isinstance(items, dict):
                visit(items)

        branches = schema.get("anyOf")
        if isinstance(branches, list):
            for branch in branches:
                if isinstance(branch, dict):
                    visit(branch)

        return schema

    return visit(result)