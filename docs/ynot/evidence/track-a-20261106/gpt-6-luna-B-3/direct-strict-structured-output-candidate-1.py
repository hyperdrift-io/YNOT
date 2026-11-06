def transform(payload):
    import copy

    result = copy.deepcopy(payload)

    def visit(schema, original_required=None, is_property=False):
        if not isinstance(schema, dict):
            return

        if is_property and original_required is not None and schema.get("_was_required") is False:
            _make_nullable(schema)

        schema.pop("default", None)

        if "properties" in schema:
            properties = schema["properties"]
            required = schema.get("required", [])
            if not isinstance(required, list):
                required = []
            required_set = set(required)
            schema["required"] = sorted(properties.keys())
            schema["additionalProperties"] = False
            for name, child in properties.items():
                if isinstance(child, dict):
                    child["_was_required"] = name in required_set
                    visit(child, required_set, True)
                    child.pop("_was_required", None)

        if "items" in schema:
            visit(schema["items"])

        if "anyOf" in schema and isinstance(schema["anyOf"], list):
            for branch in schema["anyOf"]:
                visit(branch)

    def _make_nullable(schema):
        t = schema.get("type")
        if isinstance(t, str):
            if t != "null":
                schema["type"] = [t, "null"]
        elif isinstance(t, list) and "null" not in t:
            schema["type"] = t + ["null"]
        enum = schema.get("enum")
        if isinstance(enum, list) and None not in enum:
            schema["enum"] = enum + [None]

    visit(result)
    return result