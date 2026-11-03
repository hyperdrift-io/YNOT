from copy import deepcopy


def transform(payload):
    """Return a strict-output schema without modifying the input."""
    result = deepcopy(payload)

    def visit(schema):
        schema.pop("default", None)

        if "properties" in schema:
            properties = schema["properties"]
            original_required = set(schema.get("required", []))
            for name, child in properties.items():
                visit(child)
                if name not in original_required:
                    kind = child["type"]
                    if isinstance(kind, str):
                        if kind != "null":
                            child["type"] = [kind, "null"]
                    elif "null" not in kind:
                        kind.append("null")
                    if "enum" in child and None not in child["enum"]:
                        child["enum"].append(None)
            schema["additionalProperties"] = False
            schema["required"] = sorted(properties)

        items = schema.get("items")
        if isinstance(items, dict):
            visit(items)
        elif isinstance(items, list):
            for child in items:
                if isinstance(child, dict):
                    visit(child)

        for branch in schema.get("anyOf", []):
            if isinstance(branch, dict):
                visit(branch)

    visit(result)
    return result
