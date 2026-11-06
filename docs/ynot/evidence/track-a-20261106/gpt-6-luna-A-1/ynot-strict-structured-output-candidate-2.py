def transform(payload):
    def walk(schema, optional=False):
        result = {}
        for key, value in schema.items():
            if key == "default":
                continue
            if key == "properties":
                original_required = schema.get("required", [])
                result[key] = {
                    name: walk(child, name not in original_required)
                    for name, child in value.items()
                }
                result["additionalProperties"] = False
                result["required"] = sorted(value)
            elif key == "items":
                result[key] = walk(value)
            elif key == "anyOf":
                result[key] = [walk(branch) for branch in value]
            else:
                result[key] = value

        if optional:
            typ = result.get("type")
            if isinstance(typ, str) and typ != "null":
                result["type"] = [typ, "null"]
            elif isinstance(typ, list) and "null" not in typ:
                result["type"] = typ + ["null"]
            enum = result.get("enum")
            if isinstance(enum, list) and None not in enum:
                result["enum"] = enum + [None]

        return result

    return walk(payload)