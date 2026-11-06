from copy import deepcopy


def transform(payload):
    def convert(schema):
        result = deepcopy(schema)
        nullable = result.pop("nullable", False)
        if nullable is True and "type" in result:
            original = result["type"]
            result["type"] = [original, "null"]

        if isinstance(result.get("properties"), dict):
            result["properties"] = {
                name: convert(child)
                for name, child in result["properties"].items()
            }

        for key in ("items", "additionalProperties", "not"):
            if isinstance(result.get(key), dict):
                result[key] = convert(result[key])

        for key in ("allOf", "anyOf", "oneOf"):
            if key in result:
                result[key] = [convert(child) for child in result[key]]

        return result

    return convert(payload)