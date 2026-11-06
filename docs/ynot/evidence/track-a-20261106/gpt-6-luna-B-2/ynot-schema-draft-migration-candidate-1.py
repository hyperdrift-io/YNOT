def transform(payload):
    import copy

    result = copy.deepcopy(payload)
    if not isinstance(result, dict):
        return result

    def visit(schema, root=False):
        if not isinstance(schema, dict):
            return

        if root:
            schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"

        if "id" in schema:
            schema["$id"] = schema.pop("id")

        if "definitions" in schema:
            schema["$defs"] = schema.pop("definitions")

        ref = schema.get("$ref")
        if isinstance(ref, str) and ref.startswith("#/definitions/"):
            schema["$ref"] = "#/$defs/" + ref[len("#/definitions/"):]

        for old, bound in (("exclusiveMinimum", "minimum"), ("exclusiveMaximum", "maximum")):
            if old in schema and isinstance(schema[old], bool):
                exclusive = schema.pop(old)
                if exclusive:
                    if bound in schema:
                        schema[old] = schema.pop(bound)

        items = schema.get("items")
        if isinstance(items, list):
            schema["prefixItems"] = [x for x in items]
            schema.pop("items", None)
            if "additionalItems" in schema:
                schema["items"] = schema.pop("additionalItems")
        else:
            schema.pop("additionalItems", None)

        dependencies = schema.pop("dependencies", None)
        if isinstance(dependencies, dict):
            required, dependent_schemas = {}, {}
            for key, value in dependencies.items():
                if isinstance(value, list) and all(isinstance(x, str) for x in value):
                    required[key] = value
                else:
                    dependent_schemas[key] = value
            if required:
                schema["dependentRequired"] = required
            if dependent_schemas:
                schema["dependentSchemas"] = dependent_schemas

        for keyword in ("properties", "patternProperties", "definitions"):
            child_map = schema.get(keyword)
            if isinstance(child_map, dict):
                for child in child_map.values():
                    visit(child)
        # Definitions were renamed above, so visit their contents via $defs too.
        child_map = schema.get("$defs")
        if isinstance(child_map, dict):
            for child in child_map.values():
                visit(child)

        items = schema.get("items")
        if isinstance(items, list):
            for child in items:
                visit(child)
        else:
            visit(items)
        visit(schema.get("prefixItems")) if False else None
        prefix = schema.get("prefixItems")
        if isinstance(prefix, list):
            for child in prefix:
                visit(child)
        visit(schema.get("additionalItems"))
        for keyword in ("additionalProperties", "not"):
            child = schema.get(keyword)
            if isinstance(child, dict):
                visit(child)
        for keyword in ("allOf", "anyOf", "oneOf"):
            children = schema.get(keyword)
            if isinstance(children, list):
                for child in children:
                    visit(child)
        dependent = schema.get("dependentSchemas")
        if isinstance(dependent, dict):
            for child in dependent.values():
                visit(child)

    visit(result, True)
    return result