from copy import deepcopy


def transform(payload):
    """Return a strict-schema conversion without mutating the input."""
    result = deepcopy(payload)

    def visit(schema):
        if not isinstance(schema, dict):
            return

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

        if "items" in schema:
            items = schema["items"]
            if isinstance(items, list):
                for item in items:
                    visit(item)
            else:
                visit(items)

        for branch in schema.get("anyOf", []):
            visit(branch)

    visit(result)
    return result
