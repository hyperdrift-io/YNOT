from copy import deepcopy


def transform(payload):
    def convert(schema):
        if not isinstance(schema, dict):
            return deepcopy(schema)

        result = {}
        for key, value in schema.items():
            if key == "nullable":
                continue
            if key == "properties":
                result[key] = {
                    name: convert(child) for name, child in value.items()
                }
            elif key in ("items", "additionalProperties", "not"):
                result[key] = convert(value)
            elif key in ("allOf", "anyOf", "oneOf"):
                result[key] = [convert(child) for child in value]
            else:
                result[key] = deepcopy(value)

        if schema.get("nullable") is True and "type" in schema:
            result["type"] = [schema["type"], "null"]

        return result

    return convert(payload)