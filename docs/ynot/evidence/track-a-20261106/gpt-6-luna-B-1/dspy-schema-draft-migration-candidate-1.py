def transform(payload):
    import copy

    schema = copy.deepcopy(payload)

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
                value = node[exclusive]
                if value is True and bound in node:
                    node[exclusive] = node.pop(bound)
                elif value is False or value is True:
                    node.pop(exclusive)

        items = node.get("items")
        if isinstance(items, list):
            node["prefixItems"] = [migrate(item) for item in items]
            node.pop("items")
            if "additionalItems" in node:
                node["items"] = migrate(node.pop("additionalItems"))
        else:
            if isinstance(items, dict):
                node["items"] = migrate(items)
            elif isinstance(items, bool):
                node["items"] = items
            node.pop("additionalItems", None)

        if "additionalProperties" in node and isinstance(node["additionalProperties"], dict):
            node["additionalProperties"] = migrate(node["additionalProperties"])
        if isinstance(node.get("not"), dict):
            node["not"] = migrate(node["not"])

        for keyword in ("allOf", "anyOf", "oneOf"):
            if isinstance(node.get(keyword), list):
                node[keyword] = [migrate(item) for item in node[keyword]]

        for keyword in ("properties", "patternProperties"):
            mapping = node.get(keyword)
            if isinstance(mapping, dict):
                node[keyword] = {
                    key: migrate(value) for key, value in mapping.items()
                }

        defs = node.get("$defs")
        if isinstance(defs, dict):
            node["$defs"] = {key: migrate(value) for key, value in defs.items()}

        dependencies = node.pop("dependencies", None)
        if isinstance(dependencies, dict):
            required = {}
            dependent_schemas = {}
            for key, value in dependencies.items():
                if isinstance(value, list) and all(isinstance(item, str) for item in value):
                    required[key] = value
                else:
                    dependent_schemas[key] = migrate(value)
            if required:
                node["dependentRequired"] = required
            if dependent_schemas:
                node["dependentSchemas"] = dependent_schemas

        return node

    return migrate(schema, is_root=True)