from copy import deepcopy


def transform(payload):
    """Convert OpenAPI 3.0 nullability in a schema to OpenAPI 3.1."""
    schema = deepcopy(payload)

    def visit(node):
        if not isinstance(node, dict):
            return

        nullable = node.pop("nullable", False)
        if nullable is True and "type" in node:
            node["type"] = [node["type"], "null"]

        for child in node.get("properties", {}).values():
            visit(child)

        for keyword in ("items", "additionalProperties", "not"):
            if keyword in node:
                visit(node[keyword])

        for keyword in ("allOf", "anyOf", "oneOf"):
            for child in node.get(keyword, []):
                visit(child)

    visit(schema)
    return schema
