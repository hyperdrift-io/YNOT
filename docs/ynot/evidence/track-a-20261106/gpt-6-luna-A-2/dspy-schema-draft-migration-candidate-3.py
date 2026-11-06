def transform(payload):
    import copy

    target = "https://json-schema.org/draft/2020-12/schema"

    def migrate(node, root=False):
        if not isinstance(node, dict):
            return node

        if root:
            node["$schema"] = target

        if "id" in node:
            node["$id"] = node.pop("id")

        ref = node.get("$ref")
        if isinstance(ref, str) and ref.startswith("#/definitions/"):
            node["$ref"] = "#/$defs/" + ref[len("#/definitions/"):]

        if "definitions" in node:
            node["$defs"] = node.pop("definitions")

        for exclusive, bound in (
            ("exclusiveMinimum", "minimum"),
            ("exclusiveMaximum", "maximum"),
        ):
            if isinstance(node.get(exclusive), bool):
                if node[exclusive] is True and bound in node:
                    node[exclusive] = node.pop(bound)
                else:
                    node.pop(exclusive)

        if isinstance(node.get("items"), list):
            node["prefixItems"] = node.pop("items")
            if "additionalItems" in node:
                node["items"] = node.pop("additionalItems")
        else:
            node.pop("additionalItems", None)

        dependencies = node.pop("dependencies", None)
        if isinstance(dependencies, dict):
            required, schemas = {}, {}
            for key, value in dependencies.items():
                if isinstance(value, list) and all(isinstance(item, str) for item in value):
                    required[key] = value
                else:
                    schemas[key] = value
            if required:
                node["dependentRequired"] = required
            if schemas:
                node["dependentSchemas"] = schemas

        def visit(value):
            if isinstance(value, dict):
                migrate(value)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        migrate(item)

        for key in ("properties", "patternProperties", "$defs"):
            value = node.get(key)
            if isinstance(value, dict):
                for child in value.values():
                    visit(child)

        for key in ("items", "prefixItems", "not"):
            if key in node:
                visit(node[key])

        if isinstance(node.get("additionalProperties"), dict):
            migrate(node["additionalProperties"])

        for key in ("allOf", "anyOf", "oneOf"):
            if isinstance(node.get(key), list):
                visit(node[key])

        if isinstance(node.get("dependentSchemas"), dict):
            for child in node["dependentSchemas"].values():
                visit(child)

        return node

    return migrate(copy.deepcopy(payload), root=True)