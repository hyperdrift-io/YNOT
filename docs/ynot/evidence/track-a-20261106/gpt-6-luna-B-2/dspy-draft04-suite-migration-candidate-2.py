def transform(payload):
    import copy

    document = copy.deepcopy(payload)

    def migrate(node, is_root=False):
        if not isinstance(node, dict):
            return node

        if is_root:
            node["$schema"] = "https://json-schema.org/draft/2020-12/schema"

        if "id" in node:
            node["$id"] = node.pop("id")

        if "definitions" in node:
            node["$defs"] = node.pop("definitions")

        ref = node.get("$ref")
        if isinstance(ref, str) and ref.startswith("#/definitions/"):
            node["$ref"] = "#/$defs/" + ref[len("#/definitions/"):]

        for exclusive, bound in (
            ("exclusiveMinimum", "minimum"),
            ("exclusiveMaximum", "maximum"),
        ):
            if exclusive in node:
                if node[exclusive] is True and bound in node:
                    node[exclusive] = node.pop(bound)
                elif node[exclusive] is True or node[exclusive] is False:
                    node.pop(exclusive)

        dependencies = node.pop("dependencies", None)
        if isinstance(dependencies, dict):
            dependent_required = {}
            dependent_schemas = {}
            for name, value in dependencies.items():
                if isinstance(value, list) and all(isinstance(item, str) for item in value):
                    dependent_required[name] = value
                else:
                    dependent_schemas[name] = migrate(value)
            if dependent_required:
                node["dependentRequired"] = dependent_required
            if dependent_schemas:
                node["dependentSchemas"] = dependent_schemas

        items = node.get("items")
        if isinstance(items, list):
            node["prefixItems"] = [migrate(item) for item in items]
            node.pop("items")
            if "additionalItems" in node:
                node["items"] = migrate(node.pop("additionalItems"))
        else:
            if isinstance(items, dict):
                node["items"] = migrate(items)
            node.pop("additionalItems", None)

        for key in ("properties", "patternProperties", "$defs"):
            mapping = node.get(key)
            if isinstance(mapping, dict):
                for name, subschema in list(mapping.items()):
                    mapping[name] = migrate(subschema)

        for key in ("additionalProperties", "not"):
            if isinstance(node.get(key), dict):
                node[key] = migrate(node[key])

        for key in ("allOf", "anyOf", "oneOf"):
            schemas = node.get(key)
            if isinstance(schemas, list):
                node[key] = [migrate(schema) for schema in schemas]

        return node

    return migrate(document, True)