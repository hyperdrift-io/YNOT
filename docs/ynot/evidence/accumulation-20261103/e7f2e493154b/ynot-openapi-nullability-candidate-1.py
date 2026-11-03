from copy import deepcopy


def transform(payload):
    """Convert OpenAPI 3.0 schema nullability to OpenAPI 3.1."""
    schema = deepcopy(payload)

    def visit(node):
        if not isinstance(node, dict):
            return

        nullable = node.pop("nullable", False)
        if nullable is True and "type" in node:
            node["type"] = [node["type"], "null"]

        # Only schema positions are traversed; annotation data stays intact.
        if "properties" in node:
            for child in node["properties"].values():
                visit(child)

        for keyword in ("items", "additionalProperties", "not"):
            if keyword in node:
                visit(node[keyword])

        for keyword in ("allOf", "anyOf", "oneOf"):
            if keyword in node:
                for child in node[keyword]:
                    visit(child)

    visit(schema)
    return schema
