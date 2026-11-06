def transform(payload):
    import copy

    document = copy.deepcopy(payload)
    draft = "https://json-schema.org/draft/2020-12/schema"

    def visit(schema, root=False):
        if not isinstance(schema, dict):
            return schema

        if root:
            schema["$schema"] = draft
        if "id" in schema:
            schema["$id"] = schema.pop("id")

        if "definitions" in schema:
            schema["$defs"] = schema.pop("definitions")

        ref = schema.get("$ref")
        if isinstance(ref, str) and ref.startswith("#/definitions/"):
            schema["$ref"] = "#/$defs/" + ref[len("#/definitions/"):]

        for old, bound in (("exclusiveMinimum", "minimum"),
                           ("exclusiveMaximum", "maximum")):
            if old in schema:
                if schema[old] is True and bound in schema:
                    schema[old] = schema.pop(bound)
                else:
                    schema.pop(old)

        items = schema.get("items")
        if isinstance(items, list):
            schema["prefixItems"] = [visit(item) for item in items]
            schema.pop("items")
            if "additionalItems" in schema:
                schema["items"] = visit(schema.pop("additionalItems"))
        else:
            if isinstance(items, dict):
                schema["items"] = visit(items)
            schema.pop("additionalItems", None)

        for key in ("properties", "patternProperties", "definitions"):
            value = schema.get(key)
            if isinstance(value, dict):
                for child in value.values():
                    visit(child)
        defs = schema.get("$defs")
        if isinstance(defs, dict):
            for child in defs.values():
                visit(child)

        for key in ("additionalProperties", "not"):
            child = schema.get(key)
            if isinstance(child, dict):
                visit(child)

        for key in ("allOf", "anyOf", "oneOf"):
            children = schema.get(key)
            if isinstance(children, list):
                for child in children:
                    visit(child)

        dependencies = schema.pop("dependencies", None)
        if isinstance(dependencies, dict):
            required, dependent = {}, {}
            for key, value in dependencies.items():
                if isinstance(value, list) and all(isinstance(x, str) for x in value):
                    required[key] = value
                elif isinstance(value, dict) or isinstance(value, bool):
                    dependent[key] = visit(value)
            if required:
                schema["dependentRequired"] = required
            if dependent:
                schema["dependentSchemas"] = dependent

        return schema

    return visit(document, root=True)