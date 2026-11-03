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
                    value_type = child["type"]
                    if isinstance(value_type, str):
                        if value_type != "null":
                            child["type"] = [value_type, "null"]
                    elif "null" not in value_type:
                        child["type"] = value_type + ["null"]

                    if "enum" in child:
                        if not any(value is None for value in child["enum"]):
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