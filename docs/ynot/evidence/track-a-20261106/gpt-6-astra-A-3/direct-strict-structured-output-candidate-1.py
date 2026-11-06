from copy import deepcopy


def transform(payload):
    def visit(schema):
        if not isinstance(schema, dict):
            return deepcopy(schema)

        result = {
            key: deepcopy(value)
            for key, value in schema.items()
            if key != "default"
        }

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
                    if "enum" in converted and not any(
                        value is None for value in converted["enum"]
                    ):
                        converted["enum"].append(None)
                properties[name] = converted
            result["properties"] = properties
            result["additionalProperties"] = False
            result["required"] = sorted(properties)

        if "items" in schema:
            items = schema["items"]
            result["items"] = (
                [visit(item) for item in items]
                if isinstance(items, list)
                else visit(items)
            )

        if "anyOf" in schema:
            result["anyOf"] = [visit(branch) for branch in schema["anyOf"]]

        return result

    return visit(payload)
