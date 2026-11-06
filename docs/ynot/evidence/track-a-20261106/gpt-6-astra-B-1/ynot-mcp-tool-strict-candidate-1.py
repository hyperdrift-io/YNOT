from copy import deepcopy


def transform(payload):
    result = deepcopy(payload)

    def visit(schema):
        if not isinstance(schema, dict):
            return

        schema.pop("default", None)

        if "properties" in schema:
            properties = schema["properties"]
            originally_required = set(schema.get("required", []))
            for name, child in properties.items():
                if name not in originally_required:
                    property_type = child["type"]
                    if isinstance(property_type, str):
                        if property_type != "null":
                            child["type"] = [property_type, "null"]
                    elif "null" not in property_type:
                        child["type"] = property_type + ["null"]
                    if "enum" in child and not any(
                        value is None for value in child["enum"]
                    ):
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

    visit(result)
    return result
