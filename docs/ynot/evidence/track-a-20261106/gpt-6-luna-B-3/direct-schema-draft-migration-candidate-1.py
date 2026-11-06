def transform(payload):
    import copy

    result = copy.deepcopy(payload)
    target_dialect = "https://json-schema.org/draft/2020-12/schema"
    schema_maps = ("properties", "patternProperties", "definitions")
    schema_arrays = ("allOf", "anyOf", "oneOf")

    def walk(schema, root=False):
        if not isinstance(schema, dict):
            return

        if root:
            schema["$schema"] = target_dialect
        if "id" in schema:
            schema["$id"] = schema.pop("id")
        if "definitions" in schema:
            schema["$defs"] = schema.pop("definitions")

        ref = schema.get("$ref")
        if isinstance(ref, str) and ref.startswith("#/definitions/"):
            schema["$ref"] = "#/$defs/" + ref[len("#/definitions/"):]

        for old, bound in (("exclusiveMinimum", "minimum"), ("exclusiveMaximum", "maximum")):
            if old in schema:
                flag = schema[old]
                if flag is True:
                    if bound in schema:
                        schema[old] = schema.pop(bound)
                    else:
                        schema.pop(old)
                elif flag is False:
                    schema.pop(old)

        items = schema.get("items")
        if isinstance(items, list):
            schema["prefixItems"] = items
            schema["items"] = schema.pop("additionalItems") if "additionalItems" in schema else True
            for child in items:
                walk(child)
        else:
            schema.pop("additionalItems", None)
            if isinstance(items, dict):
                walk(items)

        for key in schema_maps:
            value = schema.get(key)
            if isinstance(value, dict):
                for child in value.values():
                    walk(child)

        for key in ("additionalProperties", "not"):
            child = schema.get(key)
            if isinstance(child, dict):
                walk(child)

        for key in schema_arrays:
            value = schema.get(key)
            if isinstance(value, list):
                for child in value:
                    walk(child)

        dependencies = schema.pop("dependencies", None)
        if isinstance(dependencies, dict):
            required, dependent_schemas = {}, {}
            for name, value in dependencies.items():
                if isinstance(value, list) and all(isinstance(item, str) for item in value):
                    required[name] = value
                elif isinstance(value, dict):
                    dependent_schemas[name] = value
                    walk(value)
            if required:
                schema["dependentRequired"] = required
            if dependent_schemas:
                schema["dependentSchemas"] = dependent_schemas

    walk(result, True)
    return result