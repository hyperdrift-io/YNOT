def transform(payload):
    def convert(schema):
        if not isinstance(schema, dict):
            return schema

        result = dict(schema)
        nullable = result.pop("nullable", False)
        schema_type = result.get("type")

        if nullable is True and isinstance(schema_type, str):
            result["type"] = [schema_type, "null"]

        properties = result.get("properties")
        if isinstance(properties, dict):
            result["properties"] = {
                name: convert(subschema) for name, subschema in properties.items()
            }

        for key in ("items", "additionalProperties", "not"):
            value = result.get(key)
            if isinstance(value, dict):
                result[key] = convert(value)

        for key in ("allOf", "anyOf", "oneOf"):
            value = result.get(key)
            if isinstance(value, list):
                result[key] = [convert(subschema) for subschema in value]

        return result

    return convert(payload)