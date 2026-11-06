from copy import deepcopy


def transform(payload):
    def convert(schema):
        if not isinstance(schema, dict):
            return deepcopy(schema)

        result = deepcopy(schema)
        result.pop("default", None)

        if "properties" in schema:
            original_required = set(schema.get("required", []))
            properties = {}
            for name, child in schema["properties"].items():
                converted = convert(child)
                if name not in original_required:
                    property_type = converted["type"]
                    if isinstance(property_type, str):
                        if property_type != "null":
                            converted["type"] = [property_type, "null"]
                    elif "null" not in property_type:
                        converted["type"] = property_type + ["null"]
                    if "enum" in converted:
                        if not any(value is None for value in converted["enum"]):
                            converted["enum"].append(None)
                properties[name] = converted
            result["properties"] = properties
            result["additionalProperties"] = False
            result["required"] = sorted(properties)

        if "items" in schema:
            items = schema["items"]
            result["items"] = (
                [convert(item) for item in items]
                if isinstance(items, list)
                else convert(items)
            )

        if "anyOf" in schema:
            result["anyOf"] = [convert(branch) for branch in schema["anyOf"]]

        return result

    return convert(payload)