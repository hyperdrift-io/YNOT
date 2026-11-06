def transform(payload):
    import copy

    schema = copy.deepcopy(payload)

    def migrate(node, is_root=False):
        if not isinstance(node, dict):
            return node

        if "id" in node:
            node["$id"] = node.pop("id")
        if "definitions" in node:
            node["$defs"] = node.pop("definitions")

        if is_root:
            node["$schema"] = "https://json-schema.org/draft/2020-12/schema"

        ref = node.get("$ref")
        if isinstance(ref, str) and ref.startswith("#/definitions/"):
            node["$ref"] = "#/$defs/" + ref[len("#/definitions/"):]

        for old, bound in (("exclusiveMinimum", "minimum"),
                           ("exclusiveMaximum", "maximum")):
            if old in node:
                if node[old] is True and bound in node:
                    node[old] = node.pop(bound)
                elif node[old] is False or node[old] is True:
                    node.pop(old)

        if "dependencies" in node:
            required = {}
            dependent_schemas = {}
            for key, value in node.pop("dependencies").items():
                if isinstance(value, list) and all(isinstance(x, str) for x in value):
                    required[key] = value
                else:
                    dependent_schemas[key] = value
            if required:
                node["dependentRequired"] = required
            if dependent_schemas:
                node["dependentSchemas"] = dependent_schemas

        items = node.get("items")
        if isinstance(items, list):
            node["prefixItems"] = [migrate(x) for x in items]
            node.pop("items")
            if "additionalItems" in node:
                node["items"] = migrate(node.pop("additionalItems"))
        else:
            if isinstance(items, dict):
                node["items"] = migrate(items)
            node.pop("additionalItems", None)

        for key in ("properties", "patternProperties", "$defs"):
            value = node.get(key)
            if isinstance(value, dict):
                for name, subschema in list(value.items()):
                    value[name] = migrate(subschema)

        for key in ("not", "additionalProperties"):
            value = node.get(key)
            if isinstance(value, dict):
                node[key] = migrate(value)

        for key in ("allOf", "anyOf", "oneOf"):
            value = node.get(key)
            if isinstance(value, list):
                node[key] = [migrate(x) for x in value]

        return node

    return migrate(schema, True)