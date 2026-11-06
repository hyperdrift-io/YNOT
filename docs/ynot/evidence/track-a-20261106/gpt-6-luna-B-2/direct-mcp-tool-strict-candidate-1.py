def transform(payload):
    import copy

    result = copy.deepcopy(payload)

    def visit(schema, parent_required=None, property_name=None):
        if not isinstance(schema, dict):
            return schema

        was_optional = property_name is not None and property_name not in (parent_required or [])
        schema.pop("default", None)

        if was_optional:
            typ = schema.get("type")
            if isinstance(typ, str):
                if typ != "null":
                    schema["type"] = [typ, "null"]
            elif isinstance(typ, list) and "null" not in typ:
                schema["type"] = typ + ["null"]
            enum = schema.get("enum")
            if isinstance(enum, list) and None not in enum:
                schema["enum"] = enum + [None]

        if "properties" in schema:
            properties = schema["properties"]
            original_required = schema.get("required", [])
            if not isinstance(original_required, list):
                original_required = []
            schema["additionalProperties"] = False
            schema["required"] = sorted(properties.keys())
            for name, child in properties.items():
                properties[name] = visit(child, original_required, name)

        if "items" in schema:
            schema["items"] = visit(schema["items"])

        if "anyOf" in schema:
            schema["anyOf"] = [visit(branch) for branch in schema["anyOf"]]

        return schema

    return visit(result)
