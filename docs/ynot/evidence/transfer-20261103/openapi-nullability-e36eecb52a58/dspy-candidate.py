from copy import deepcopy


def transform(payload):
    def convert(schema):
        result = deepcopy(schema)
        nullable = result.pop("nullable", False)

        if nullable is True and "type" in result:
            original_type = result["type"]
            result["type"] = [original_type, "null"]

        if "properties" in result:
            result["properties"] = {
                name: convert(child)
                for name, child in result["properties"].items()
            }

        for keyword in ("items", "additionalProperties", "not"):
            if keyword in result and isinstance(result[keyword], dict):
                result[keyword] = convert(result[keyword])

        for keyword in ("allOf", "anyOf", "oneOf"):
            if keyword in result:
                result[keyword] = [convert(child) for child in result[keyword]]

        return result

    return convert(payload)