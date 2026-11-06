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
            for name, prop in properties.items():
                visit(prop)
                if name not in original_required:
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
