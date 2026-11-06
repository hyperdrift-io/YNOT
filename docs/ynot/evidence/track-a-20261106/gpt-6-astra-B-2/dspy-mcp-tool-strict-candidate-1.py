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
                    kind = converted.get("type")
                    if isinstance(kind, str) and kind != "null":
                        converted["type"] = [kind, "null"]
                    elif isinstance(kind, list) and "null" not in kind:
                        converted["type"] = kind + ["null"]
                    if "enum" in converted:
                        if not any(value is None for value in converted["enum"]):
                            converted["enum"].append(None)
                properties[name] = converted
            result["properties"] = properties
            result["required"] = sorted(properties)
            result["additionalProperties"] = False

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