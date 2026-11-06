def transform(payload):
    import copy

    def convert(schema, optional=False):
        result = copy.deepcopy(schema)
        result.pop("default", None)

        if "properties" in result:
            properties = result["properties"]
            original_required = set(result.get("required", []))
            result["properties"] = {
                name: convert(value, name not in original_required)
                for name, value in properties.items()
            }
            result["required"] = sorted(properties)
            result["additionalProperties"] = False

        if "items" in result:
            result["items"] = convert(result["items"])

        if "anyOf" in result:
            result["anyOf"] = [convert(branch) for branch in result["anyOf"]]

        if optional:
            schema_type = result.get("type")
            if isinstance(schema_type, str):
                if schema_type != "null":
                    result["type"] = [schema_type, "null"]
            elif isinstance(schema_type, list) and "null" not in schema_type:
                result["type"] = schema_type + ["null"]

            if "enum" in result and None not in result["enum"]:
                result["enum"] = result["enum"] + [None]

        return result

    return convert(payload)