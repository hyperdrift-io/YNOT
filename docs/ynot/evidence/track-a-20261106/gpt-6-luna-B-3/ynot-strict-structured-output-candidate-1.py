def transform(payload):
    def visit(schema, parent_required=None, name=None):
        # Work on a fresh tree so the input remains unchanged.
        result = {}
        was_optional = parent_required is not None and name not in parent_required
        for key, value in schema.items():
            if key == "default":
                continue
            if key == "properties":
                required = schema.get("required", [])
                result[key] = {
                    prop: visit(child, required, prop)
                    for prop, child in value.items()
                }
            elif key == "items":
                result[key] = visit(value)
            elif key == "anyOf":
                result[key] = [visit(branch) for branch in value]
            else:
                result[key] = value
        if "properties" in schema:
            result["additionalProperties"] = False
            result["required"] = sorted(schema["properties"].keys())
        if was_optional:
            typ = schema["type"]
            if isinstance(typ, str):
                if typ != "null":
                    result["type"] = [typ, "null"]
            elif "null" not in typ:
                result["type"] = list(typ) + ["null"]
            if "enum" in schema and None not in schema["enum"]:
                result["enum"] = list(schema["enum"]) + [None]
        return result
    return visit(payload)