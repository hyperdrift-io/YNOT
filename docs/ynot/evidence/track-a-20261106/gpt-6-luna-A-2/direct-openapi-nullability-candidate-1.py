def transform(payload):
    import copy

    schema = copy.deepcopy(payload)

    def visit(node):
        if not isinstance(node, dict):
            return node

        nullable = node.pop("nullable", False)
        original_type = node.get("type")
        if nullable is True and isinstance(original_type, str):
            node["type"] = [original_type, "null"]

        for key in ("properties",):
            children = node.get(key)
            if isinstance(children, dict):
                for name, child in children.items():
                    children[name] = visit(child)

        for key in ("items", "additionalProperties", "not"):
            child = node.get(key)
            if isinstance(child, dict):
                node[key] = visit(child)

        for key in ("allOf", "anyOf", "oneOf"):
            children = node.get(key)
            if isinstance(children, list):
                node[key] = [visit(child) for child in children]

        return node

    return visit(schema)