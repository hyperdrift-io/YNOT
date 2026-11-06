def transform(payload):
    def visit(schema, parent_required=None, name=None):
        result = {}
        was_optional = parent_required is not None and name not in parent_required
        for key, value in schema.items():
            if key == "default":
                continue
            if key == "properties":
                result[key] = {
                    prop_name: visit(prop_schema, schema.get("required", []), prop_name)
                    for prop_name, prop_schema in value.items()
                }
            elif key == "items":
                result[key] = visit(value)
            elif key == "anyOf":
                result[key] = [visit(branch) for branch in value]
            else:
                result[key] = value
        if "properties" in schema:
            result["additionalProperties"] = False
            result["required"] = sorted(schema["properties"].keys())
        if was_optional:
            typ = result.get("type")
            if isinstance(typ, str) and typ != "null":
                result["type"] = [typ, "null"]
            elif isinstance(typ, list) and "null" not in typ:
                result["type"] = typ + ["null"]
            enum = result.get("enum")
            if isinstance(enum, list) and None not in enum:
                result["enum"] = enum + [None]
        return result

    return visit(payload)
