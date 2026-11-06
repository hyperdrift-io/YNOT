from copy import deepcopy


def transform(payload):
    """Convert a JSON Schema to the requested strict subset without mutation."""
    def convert(schema):
        if not isinstance(schema, dict):
            return deepcopy(schema)

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
                    if "enum" in prop and not any(
                        value is None for value in prop["enum"]
                    ):
                        prop["enum"].append(None)
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
