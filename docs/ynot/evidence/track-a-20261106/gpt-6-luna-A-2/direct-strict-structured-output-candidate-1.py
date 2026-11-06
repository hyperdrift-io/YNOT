def transform(payload):
    import copy

    def convert(schema, parent_required=None, property_name=None):
        result = copy.deepcopy(schema)
        result.pop("default", None)

        if parent_required is not None and property_name not in parent_required:
            typ = result.get("type")
            if isinstance(typ, str):
                if typ != "null":
                    result["type"] = [typ, "null"]
            elif isinstance(typ, list) and "null" not in typ:
                result["type"] = typ + ["null"]
            enum = result.get("enum")
            if isinstance(enum, list) and None not in enum:
                result["enum"] = enum + [None]

        if "properties" in result:
            properties = result["properties"]
            original_required = result.get("required", [])
            result["properties"] = {
                name: convert(value, original_required, name)
                for name, value in properties.items()
            }
            result["additionalProperties"] = False
            result["required"] = sorted(properties)

        if "items" in result:
            result["items"] = convert(result["items"])
        if "anyOf" in result:
            result["anyOf"] = [convert(branch) for branch in result["anyOf"]]
        return result

    return convert(payload)
