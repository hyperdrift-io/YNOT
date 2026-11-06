def transform(payload):
    import copy

    result = copy.deepcopy(payload)

    def visit(schema, originally_required=False):
        schema.pop("default", None)

        if "properties" in schema:
            properties = schema["properties"]
            required = schema.get("required", [])
            required_set = set(required)
            for name in sorted(properties):
                visit(properties[name], name not in required_set)
            schema["additionalProperties"] = False
            schema["required"] = sorted(properties)

        if "items" in schema:
            visit(schema["items"])

        if "anyOf" in schema:
            for branch in schema["anyOf"]:
                visit(branch)

        if originally_required:
            schema_type = schema["type"]
            if isinstance(schema_type, str):
                if schema_type != "null":
                    schema["type"] = [schema_type, "null"]
            elif "null" not in schema_type:
                schema["type"] = schema_type + ["null"]

            if "enum" in schema and None not in schema["enum"]:
                schema["enum"].append(None)

    visit(result)
    return result