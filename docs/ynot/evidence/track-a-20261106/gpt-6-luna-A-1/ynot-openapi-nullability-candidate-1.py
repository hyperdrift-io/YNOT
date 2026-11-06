def transform(payload):
    def convert(schema):
        if isinstance(schema, bool):
            return schema
        if not isinstance(schema, dict):
            return schema

        result = {}
        for key, value in schema.items():
            if key == "nullable":
                continue
            if key == "type" and schema.get("nullable") is True:
                if isinstance(value, str):
                    result[key] = [value, "null"]
                elif isinstance(value, list):
                    result[key] = [item for item in value if item != "null"] + ["null"]
                else:
                    result[key] = value
            elif key == "properties" and isinstance(value, dict):
                result[key] = {name: convert(child) for name, child in value.items()}
            elif key == "items":
                result[key] = convert(value)
            elif key == "additionalProperties" and isinstance(value, dict):
                result[key] = convert(value)
            elif key in ("allOf", "anyOf", "oneOf") and isinstance(value, list):
                result[key] = [convert(child) for child in value]
            elif key == "not":
                result[key] = convert(value)
            else:
                result[key] = value

        if schema.get("nullable") is True and "type" not in schema:
            result.pop("nullable", None)
        return result

    return convert(payload)