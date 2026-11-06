def transform(payload):
    import copy

    result = copy.deepcopy(payload)
    if not isinstance(result, dict):
        return result

    def walk(schema, root=False):
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
                if schema[old] is True and bound in schema:
                    schema[old] = schema.pop(bound)
                else:
                    schema.pop(old)

        if isinstance(schema.get("items"), list):
            schema["prefixItems"] = schema.pop("items")
            if "additionalItems" in schema:
                schema["items"] = schema.pop("additionalItems")
        else:
            schema.pop("additionalItems", None)

        dependencies = schema.pop("dependencies", None)
        if isinstance(dependencies, dict):
            required, dependent_schemas = {}, {}
            for key, value in dependencies.items():
                if isinstance(value, list) and all(isinstance(item, str) for item in value):
                    required[key] = value
                else:
                    dependent_schemas[key] = value
                    walk(value)
            if required:
                schema["dependentRequired"] = required
            if dependent_schemas:
                schema["dependentSchemas"] = dependent_schemas

        for keyword in ("properties", "patternProperties", "$defs"):
            children = schema.get(keyword)
            if isinstance(children, dict):
                for child in children.values():
                    walk(child)

        for keyword in ("items", "additionalItems", "additionalProperties", "not"):
            child = schema.get(keyword)
            if isinstance(child, dict):
                walk(child)

        for keyword in ("prefixItems", "allOf", "anyOf", "oneOf"):
            children = schema.get(keyword)
            if isinstance(children, list):
                for child in children:
                    walk(child)

    walk(result, True)
    return result