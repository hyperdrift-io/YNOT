def transform(payload):
    import copy

    schema = copy.deepcopy(payload)
    if not isinstance(schema, dict):
        return schema

    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"

    def migrate(node, *, root=False):
        if not isinstance(node, dict):
            return

        if "id" in node:
            node["$id"] = node.pop("id")

        if "definitions" in node:
            node["$defs"] = node.pop("definitions")

        ref = node.get("$ref")
        if isinstance(ref, str) and ref.startswith("#/definitions/"):
            node["$ref"] = "#/$defs/" + ref[len("#/definitions/"):]

        for exclusive, bound in (("exclusiveMinimum", "minimum"),
                                 ("exclusiveMaximum", "maximum")):
            if exclusive in node:
                value = node[exclusive]
                if value is True and bound in node:
                    node[exclusive] = node.pop(bound)
                elif value is False or value is True:
                    node.pop(exclusive)

        items = node.get("items")
        if isinstance(items, list):
            node["prefixItems"] = items
            node.pop("items")
            if "additionalItems" in node:
                node["items"] = node.pop("additionalItems")
        elif "additionalItems" in node:
            node.pop("additionalItems")

        dependencies = node.pop("dependencies", None)
        if isinstance(dependencies, dict):
            required, dependent_schemas = {}, {}
            for key, value in dependencies.items():
                if isinstance(value, list) and all(isinstance(item, str) for item in value):
                    required[key] = value
                else:
                    dependent_schemas[key] = value
            if required:
                node["dependentRequired"] = required
            if dependent_schemas:
                node["dependentSchemas"] = dependent_schemas

        schema_maps = ("properties", "patternProperties", "$defs")
        for keyword in schema_maps:
            mapping = node.get(keyword)
            if isinstance(mapping, dict):
                for child in mapping.values():
                    migrate(child)

        for keyword in ("items", "prefixItems", "additionalItems",
                        "additionalProperties", "not"):
            child = node.get(keyword)
            if isinstance(child, list):
                for member in child:
                    migrate(member)
            else:
                migrate(child)

        for keyword in ("allOf", "anyOf", "oneOf"):
            children = node.get(keyword)
            if isinstance(children, list):
                for child in children:
                    migrate(child)

        dependent = node.get("dependentSchemas")
        if isinstance(dependent, dict):
            for child in dependent.values():
                migrate(child)

    migrate(schema, root=True)
    return schema