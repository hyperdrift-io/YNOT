def transform(payload):
    import copy

    result = copy.deepcopy(payload)

    def visit(schema, parent_required=None, is_property=False):
        if not isinstance(schema, dict):
            return

        was_required = is_property and schema.get("_original_required", False)
        schema.pop("default", None)

        if "properties" in schema and isinstance(schema["properties"], dict):
            properties = schema["properties"]
            required = schema.get("required", [])
            required_set = set(required) if isinstance(required, list) else set()

            for child in properties.values():
                if isinstance(child, dict):
                    child["_original_required"] = False

            for name, child in properties.items():
                if isinstance(child, dict):
                    child["_original_required"] = name in required_set
                    visit(child, is_property=True)

            schema["required"] = sorted(properties)
            schema["additionalProperties"] = False

            for child in properties.values():
                if isinstance(child, dict):
                    child.pop("_original_required", None)

        if is_property and not was_required:
            typ = schema.get("type")
            if isinstance(typ, str) and typ != "null":
                schema["type"] = [typ, "null"]
            elif isinstance(typ, list) and "null" not in typ:
                schema["type"] = typ + ["null"]

            enum = schema.get("enum")
            if isinstance(enum, list) and None not in enum:
                schema["enum"] = enum + [None]

        if "items" in schema:
            visit(schema["items"])
        if isinstance(schema.get("anyOf"), list):
            for branch in schema["anyOf"]:
                visit(branch)

    visit(result)
    return result