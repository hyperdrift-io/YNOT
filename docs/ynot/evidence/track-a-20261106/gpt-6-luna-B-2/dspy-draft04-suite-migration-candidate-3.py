def transform(payload):
    import copy

    document = copy.deepcopy(payload)
    draft_uri = "https://json-schema.org/draft/2020-12/schema"

    def migrate(node, is_root=False):
        if not isinstance(node, dict):
            return node

        if "id" in node:
            node["$id"] = node.pop("id")
        if "definitions" in node:
            node["$defs"] = node.pop("definitions")
        if is_root:
            node["$schema"] = draft_uri

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
                else:
                    node.pop(exclusive)

        dependencies = node.pop("dependencies", None)
        if isinstance(dependencies, dict):
            required, schemas = {}, {}
            for name, value in dependencies.items():
                if isinstance(value, list) and all(isinstance(item, str) for item in value):
                    required[name] = value
                else:
                    schemas[name] = migrate(value)
            if required:
                node["dependentRequired"] = required
            if schemas:
                node["dependentSchemas"] = schemas

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

        for key in ("not", "additionalProperties"):
            value = node.get(key)
            if isinstance(value, dict):
                node[key] = migrate(value)

        for key in ("allOf", "anyOf", "oneOf"):
            schemas = node.get(key)
            if isinstance(schemas, list):
                node[key] = [migrate(schema) for schema in schemas]

        return node

    return migrate(document, True)