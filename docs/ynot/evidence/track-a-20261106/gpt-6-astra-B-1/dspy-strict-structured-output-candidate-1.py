from copy import deepcopy


def transform(payload):
    def convert(schema):
        result = deepcopy(schema)
        result.pop("default", None)

        if "properties" in schema:
            originally_required = set(schema.get("required", []))
            properties = {}
            for name, original in schema["properties"].items():
                prop = convert(original)
                if name not in originally_required:
                    kind = prop["type"]
                    if isinstance(kind, str):
                        if kind != "null":
                            prop["type"] = [kind, "null"]
                    elif "null" not in kind:
                        prop["type"] = kind + ["null"]
                    if "enum" in prop and None not in prop["enum"]:
                        prop["enum"].append(None)
                properties[name] = prop
            result["properties"] = properties
            result["additionalProperties"] = False
            result["required"] = sorted(properties)

        if "items" in schema:
            items = schema["items"]
            if isinstance(items, dict):
                result["items"] = convert(items)
            elif isinstance(items, list):
                result["items"] = [
                    convert(item) if isinstance(item, dict) else deepcopy(item)
                    for item in items
                ]

        if "anyOf" in schema:
            result["anyOf"] = [
                convert(branch) if isinstance(branch, dict) else deepcopy(branch)
                for branch in schema["anyOf"]
            ]

        return result

    return convert(payload)