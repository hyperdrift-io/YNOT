from copy import deepcopy


def transform(payload):
    """Return a strict-output schema without modifying the input."""
    def visit(schema):
        result = deepcopy(schema)
        result.pop("default", None)

        if "properties" in schema:
            originally_required = set(schema.get("required", []))
            properties = {}
            for name, child in schema["properties"].items():
                converted = visit(child)
                if name not in originally_required:
                    kind = converted["type"]
                    if isinstance(kind, str):
                        if kind != "null":
                            converted["type"] = [kind, "null"]
                    elif "null" not in kind:
                        converted["type"] = kind + ["null"]
                    if "enum" in converted and None not in converted["enum"]:
                        converted["enum"].append(None)
                properties[name] = converted
            result["properties"] = properties
            result["additionalProperties"] = False
            result["required"] = sorted(properties)

        if "items" in schema:
            items = schema["items"]
            if isinstance(items, dict):
                result["items"] = visit(items)
            elif isinstance(items, list):
                result["items"] = [visit(item) if isinstance(item, dict) else deepcopy(item) for item in items]

        if "anyOf" in schema:
            result["anyOf"] = [visit(branch) if isinstance(branch, dict) else deepcopy(branch) for branch in schema["anyOf"]]

        return result

    return visit(payload)
