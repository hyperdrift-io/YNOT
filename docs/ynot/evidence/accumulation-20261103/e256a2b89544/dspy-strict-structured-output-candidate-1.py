from copy import deepcopy


def transform(payload):
    result = deepcopy(payload)

    def visit(schema):
        if not isinstance(schema, dict):
            return

        schema.pop("default", None)

        if "properties" in schema:
            properties = schema["properties"]
            original_required = set(schema.get("required", []))

            for name, child in properties.items():
                if name not in original_required:
                    kind = child["type"]
                    if isinstance(kind, str):
                        if kind != "null":
                            child["type"] = [kind, "null"]
                    elif isinstance(kind, list) and "null" not in kind:
                        kind.append("null")

                    if "enum" in child and None not in child["enum"]:
                        child["enum"].append(None)

                visit(child)

            schema["additionalProperties"] = False
            schema["required"] = sorted(properties)

        items = schema.get("items")
        if isinstance(items, dict):
            visit(items)
        elif isinstance(items, list):
            for item in items:
                visit(item)

        for branch in schema.get("anyOf", []):
            visit(branch)

    visit(result)
    return result