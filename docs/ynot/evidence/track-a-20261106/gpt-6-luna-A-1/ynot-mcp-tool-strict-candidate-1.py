def transform(payload):
    def visit(schema, parent_required=None):
        result = {}
        for key, value in schema.items():
            if key == "default":
                continue
            if key == "properties":
                result[key] = {name: visit(child, name in original_required) for name, child in value.items()}
            elif key == "items":
                result[key] = visit(value)
            elif key == "anyOf":
                result[key] = [visit(branch) for branch in value]
            else:
                result[key] = value

        if "properties" in schema:
            names = list(schema["properties"].keys())
            result["properties"] = {name: visit(child, name in original_required) for name, child in schema["properties"].items()}
            result["additionalProperties"] = False
            result["required"] = sorted(names)

        if parent_required is False:
            typ = result.get("type")
            if isinstance(typ, str) and typ != "null":
                result["type"] = [typ, "null"]
            elif isinstance(typ, list) and "null" not in typ:
                result["type"] = typ + ["null"]
            enum = result.get("enum")
            if isinstance(enum, list) and None not in enum:
                result["enum"] = enum + [None]
        return result

    original_required = set(payload.get("required", []))
    return visit(payload, True)