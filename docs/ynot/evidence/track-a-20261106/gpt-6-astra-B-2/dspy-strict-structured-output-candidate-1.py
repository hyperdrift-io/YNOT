from copy import deepcopy


def transform(payload):
    def visit(schema):
        if not isinstance(schema, dict):
            return deepcopy(schema)

        result = deepcopy(schema)
        result.pop("default", None)

        if "properties" in schema:
            original_required = set(schema.get("required", []))
            properties = {}
            for name, child in schema["properties"].items():
                converted = visit(child)
                if name not in original_required:
                    kind = converted["type"]
                    if isinstance(kind, str):
                        if kind != "null":
                            converted["type"] = [kind, "null"]
                    elif "null" not in kind:
                        converted["type"] = kind + ["null"]
                    if "enum" in converted:
                        if not any(value is None for value in converted["enum"]):
                            converted["enum"].append(None)
                properties[name] = converted
            result["properties"] = properties
            result["additionalProperties"] = False
            result["required"] = sorted(properties)

        if "items" in schema:
            items = schema["items"]
            if isinstance(items, list):
                result["items"] = [visit(item) for item in items]
            else:
                result["items"] = visit(items)

        if "anyOf" in schema:
            result["anyOf"] = [visit(branch) for branch in schema["anyOf"]]

        return result

    return visit(payload)