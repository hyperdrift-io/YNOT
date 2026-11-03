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
                visit(child)
                if name not in original_required:
                    kind = child["type"]
                    if isinstance(kind, str):
                        if kind != "null":
                            child["type"] = [kind, "null"]
                    elif "null" not in kind:
                        kind.append("null")
                    if "enum" in child and not any(
                        value is None for value in child["enum"]
                    ):
                        child["enum"].append(None)
            schema["additionalProperties"] = False
            schema["required"] = sorted(properties)

        if "items" in schema:
            items = schema["items"]
            if isinstance(items, list):
                for child in items:
                    visit(child)
            else:
                visit(items)

        for child in schema.get("anyOf", []):
            visit(child)

    visit(result)
    return result
