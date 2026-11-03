from copy import deepcopy


def transform(payload):
    schema = deepcopy(payload)

    def convert(node):
        nullable = node.pop("nullable", False)
        if nullable is True and "type" in node:
            node["type"] = [node["type"], "null"]

        for child in node.get("properties", {}).values():
            convert(child)

        for keyword in ("items", "additionalProperties", "not"):
            child = node.get(keyword)
            if isinstance(child, dict):
                convert(child)

        for keyword in ("allOf", "anyOf", "oneOf"):
            for child in node.get(keyword, []):
                convert(child)

    convert(schema)
    return schema
