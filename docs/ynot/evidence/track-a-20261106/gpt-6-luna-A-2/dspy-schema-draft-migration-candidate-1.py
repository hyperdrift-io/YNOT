def transform(payload):
    import copy

    schema = copy.deepcopy(payload)
    target = "https://json-schema.org/draft/2020-12/schema"

    def migrate(node, root=False):
        if not isinstance(node, dict):
            return node

        if root:
            node["$schema"] = target

        if "id" in node:
            node["$id"] = node.pop("id")

        if "$ref" in node and isinstance(node["$ref"], str):
            ref = node["$ref"]
            prefix = "#/definitions/"
            if ref.startswith(prefix):
                node["$ref"] = "#/$defs/" + ref[len(prefix):]

        if "definitions" in node:
            node["$defs"] = node.pop("definitions")

        for exclusive, bound in (
            ("exclusiveMinimum", "minimum"),
            ("exclusiveMaximum", "maximum"),
        ):
            if exclusive in node and isinstance(node[exclusive], bool):
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
            required = {}
            schemas = {}
            for key, value in dependencies.items():
                if isinstance(value, list) and all(isinstance(item, str) for item in value):
                    required[key] = value
                else:
                    schemas[key] = value
            if required:
                node["dependentRequired"] = required
            else:
                node.pop("dependentRequired", None)
            if schemas:
                node["dependentSchemas"] = schemas
            else:
                node.pop("dependentSchemas", None)

        def migrate_value(value):
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
                    migrate_value(child)

        for key in ("items", "prefixItems", "additionalItems", "additionalProperties", "not"):
            if key in node:
                migrate_value(node[key])

        for key in ("allOf", "anyOf", "oneOf"):
            value = node.get(key)
            if isinstance(value, list):
                for child in value:
                    migrate_value(child)

        for key in ("dependentSchemas",):
            value = node.get(key)
            if isinstance(value, dict):
                for child in value.values():
                    migrate_value(child)

        return node

    return migrate(schema, root=True)