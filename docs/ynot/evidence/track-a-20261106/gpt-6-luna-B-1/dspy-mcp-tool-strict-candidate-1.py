def transform(payload):
    import copy

    schema = copy.deepcopy(payload)

    def visit(node, optional=False):
        if not isinstance(node, dict):
            return node

        original_required = node.get("required", [])
        properties = node.get("properties")

        if properties is not None:
            required_names = sorted(properties)
            node["additionalProperties"] = False
            node["required"] = required_names

            for name, child in properties.items():
                was_required = name in original_required
                visit(child, optional=not was_required)

        if "items" in node:
            visit(node["items"])

        if "anyOf" in node:
            for branch in node["anyOf"]:
                visit(branch)

        node.pop("default", None)

        if optional:
            typ = node.get("type")
            if isinstance(typ, str):
                if typ != "null":
                    node["type"] = [typ, "null"]
            elif isinstance(typ, list) and "null" not in typ:
                node["type"] = typ + ["null"]

            enum = node.get("enum")
            if isinstance(enum, list) and None not in enum:
                node["enum"] = enum + [None]

        return node

    return visit(schema)