def transform(payload):
    import copy

    result = copy.deepcopy(payload)

    def visit(schema, optional=False):
        schema.pop("default", None)

        if optional:
            schema_type = schema["type"]
            if isinstance(schema_type, str):
                if schema_type != "null":
                    schema["type"] = [schema_type, "null"]
            elif "null" not in schema_type:
                schema["type"] = schema_type + ["null"]

            if "enum" in schema and None not in schema["enum"]:
                schema["enum"].append(None)

        if "properties" in schema:
            properties = schema["properties"]
            originally_required = set(schema.get("required", []))
            for name, child in properties.items():
                visit(child, name not in originally_required)
            schema["additionalProperties"] = False
            schema["required"] = sorted(properties)

        if "items" in schema:
            visit(schema["items"])

        if "anyOf" in schema:
            for branch in schema["anyOf"]:
                visit(branch)

    visit(result)
    return result