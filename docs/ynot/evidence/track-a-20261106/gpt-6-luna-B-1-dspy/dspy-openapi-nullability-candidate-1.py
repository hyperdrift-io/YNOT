def transform(payload):
    import copy

    result = copy.deepcopy(payload)

    def convert(schema):
        if not isinstance(schema, dict):
            return

        nullable = schema.pop("nullable", False)
        if nullable is True and "type" in schema:
            original = schema["type"]
            if isinstance(original, str):
                if original != "null":
                    schema["type"] = [original, "null"]
            elif isinstance(original, list):
                schema["type"] = [item for item in original if item != "null"] + ["null"]

        properties = schema.get("properties")
        if isinstance(properties, dict):
            for child in properties.values():
                convert(child)

        for key in ("items", "additionalProperties", "not"):
            child = schema.get(key)
            if isinstance(child, dict):
                convert(child)

        for key in ("allOf", "anyOf", "oneOf"):
            children = schema.get(key)
            if isinstance(children, list):
                for child in children:
                    convert(child)

    convert(result)
    return result