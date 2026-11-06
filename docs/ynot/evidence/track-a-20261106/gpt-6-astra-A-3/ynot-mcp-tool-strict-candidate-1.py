from copy import deepcopy


def transform(payload):
    """Convert an MCP input schema without mutating the input."""
    def convert(schema, optional=False):
        if not isinstance(schema, dict):
            return deepcopy(schema)

        result = deepcopy(schema)
        result.pop("default", None)

        if "properties" in schema:
            originally_required = set(schema.get("required", []))
            result["properties"] = {
                name: convert(child, name not in originally_required)
                for name, child in schema["properties"].items()
            }
            result["required"] = sorted(schema["properties"])
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

        if optional:
            kind = result.get("type")
            if isinstance(kind, str) and kind != "null":
                result["type"] = [kind, "null"]
            elif isinstance(kind, list) and "null" not in kind:
                result["type"] = kind + ["null"]
            if "enum" in result and None not in result["enum"]:
                result["enum"].append(None)

        return result

    return convert(payload)
