from copy import deepcopy


def transform(payload):
    def convert(schema):
        if not isinstance(schema, dict):
            return deepcopy(schema)

        result = deepcopy(schema)
        result.pop("default", None)

        if "properties" in schema:
            original_required = schema.get("required", [])
            properties = {}
            for name, original in schema["properties"].items():
                prop = convert(original)
                if name not in original_required:
                    kind = prop.get("type")
                    if isinstance(kind, str) and kind != "null":
                        prop["type"] = [kind, "null"]
                    elif isinstance(kind, list) and "null" not in kind:
                        prop["type"] = kind + ["null"]
                    if "enum" in prop and None not in prop["enum"]:
                        prop["enum"] = prop["enum"] + [None]
                properties[name] = prop
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