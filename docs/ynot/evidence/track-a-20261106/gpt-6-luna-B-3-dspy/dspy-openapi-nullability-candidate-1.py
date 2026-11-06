def transform(payload):
    def convert(schema):
        if isinstance(schema, bool):
            return schema
        if not isinstance(schema, dict):
            return schema

        result = dict(schema)
        nullable = result.pop("nullable", None)
        original_type = result.get("type")
        if nullable is True and original_type is not None:
            if isinstance(original_type, list):
                types = [t for t in original_type if t != "null"]
                result["type"] = types + ["null"]
            else:
                result["type"] = [original_type, "null"]

        properties = result.get("properties")
        if isinstance(properties, dict):
            result["properties"] = {
                name: convert(subschema) for name, subschema in properties.items()
            }

        for key in ("items", "additionalProperties", "not"):
            value = result.get(key)
            if isinstance(value, (dict, bool)):
                result[key] = convert(value)

        for key in ("allOf", "anyOf", "oneOf"):
            value = result.get(key)
            if isinstance(value, list):
                result[key] = [convert(subschema) for subschema in value]

        return result

    return convert(payload)