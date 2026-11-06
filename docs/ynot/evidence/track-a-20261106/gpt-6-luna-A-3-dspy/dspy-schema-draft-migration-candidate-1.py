def transform(payload):
    import copy

    schema = copy.deepcopy(payload)
    if not isinstance(schema, dict):
        return schema

    def migrate(node, root=False):
        if not isinstance(node, dict):
            return

        if root:
            node["$schema"] = "https://json-schema.org/draft/2020-12/schema"

        if "id" in node:
            node["$id"] = node.pop("id")

        if "definitions" in node:
            node["$defs"] = node.pop("definitions")

        ref = node.get("$ref")
        if isinstance(ref, str) and ref.startswith("#/definitions/"):
            node["$ref"] = "#/$defs/" + ref[len("#/definitions/"):]

        for old, bound in (("exclusiveMinimum", "minimum"),
                           ("exclusiveMaximum", "maximum")):
            if old in node:
                flag = node[old]
                if flag is True and bound in node:
                    node[old] = node.pop(bound)
                elif flag is False or flag is True:
                    node.pop(old)

        items = node.get("items")
        if isinstance(items, list):
            node["prefixItems"] = node.pop("items")
            if "additionalItems" in node:
                node["items"] = node.pop("additionalItems")
        else:
            node.pop("additionalItems", None)

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

        for keyword in ("properties", "patternProperties", "$defs"):
            children = node.get(keyword)
            if isinstance(children, dict):
                for child in children.values():
                    migrate(child)

        for keyword in ("items", "prefixItems", "additionalItems",
                        "additionalProperties", "not"):
            child = node.get(keyword)
            if isinstance(child, dict):
                migrate(child)
            elif isinstance(child, list):
                for item in child:
                    migrate(item)

        for keyword in ("allOf", "anyOf", "oneOf"):
            children = node.get(keyword)
            if isinstance(children, list):
                for child in children:
                    migrate(child)

        for keyword in ("dependentSchemas",):
            children = node.get(keyword)
            if isinstance(children, dict):
                for child in children.values():
                    migrate(child)

    migrate(schema, True)
    return schema