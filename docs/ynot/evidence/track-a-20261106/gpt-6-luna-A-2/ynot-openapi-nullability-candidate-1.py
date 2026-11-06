def transform(payload):
    import copy

    schema = copy.deepcopy(payload)

    def visit(node):
        if isinstance(node, bool):
            return node
        if not isinstance(node, dict):
            return node

        nullable = node.pop("nullable", False)
        if nullable is True and "type" in node:
            original_type = node["type"]
            if isinstance(original_type, str):
                node["type"] = [original_type, "null"]
            elif isinstance(original_type, list) and "null" not in original_type:
                node["type"] = [*original_type, "null"]

        for key in ("properties",):
            value = node.get(key)
            if isinstance(value, dict):
                for child_key, child in value.items():
                    value[child_key] = visit(child)

        for key in ("items", "additionalProperties", "not"):
            if key in node and isinstance(node[key], (dict, bool)):
                node[key] = visit(node[key])

        for key in ("allOf", "anyOf", "oneOf"):
            value = node.get(key)
            if isinstance(value, list):
                node[key] = [visit(child) for child in value]

        return node

    return visit(schema)