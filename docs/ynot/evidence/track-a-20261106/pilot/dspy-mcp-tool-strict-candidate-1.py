from copy import deepcopy


def transform(payload):
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
                    elif isinstance(kind, list) and "null" not in kind:
                        child["type"] = kind + ["null"]
                    if "enum" in child:
                        if not any(value is None for value in child["enum"]):
                            child["enum"].append(None)
            schema["additionalProperties"] = False
            schema["required"] = sorted(properties)

        items = schema.get("items")
        if isinstance(items, dict):
            visit(items)
        elif isinstance(items, list):
            for child in items:
                visit(child)

        for branch in schema.get("anyOf", []):
            visit(branch)

    result = deepcopy(payload)
    visit(result)
    return result