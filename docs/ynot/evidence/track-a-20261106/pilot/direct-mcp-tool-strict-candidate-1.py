from copy import deepcopy


def transform(payload):
    """Return a strict-schema conversion without mutating the input."""
    def visit(schema):
        if not isinstance(schema, dict):
            return

        schema.pop("default", None)

        if "properties" in schema:
            properties = schema["properties"]
            originally_required = set(schema.get("required", []))
            for name, child in properties.items():
                if name not in originally_required:
                    kind = child["type"]
                    if isinstance(kind, str):
                        if kind != "null":
                            child["type"] = [kind, "null"]
                    elif "null" not in kind:
                        child["type"] = kind + ["null"]
                    if "enum" in child and None not in child["enum"]:
                        child["enum"].append(None)
                visit(child)
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

    result = deepcopy(payload)
    visit(result)
    return result
