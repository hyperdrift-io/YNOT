def transform(payload):
    import copy

    result = copy.deepcopy(payload)
    result["$schema"] = "https://json-schema.org/draft/2020-12/schema"

    def migrate(schema):
        if not isinstance(schema, dict):
            return

        if "id" in schema:
            schema["$id"] = schema.pop("id")

        if "definitions" in schema:
            schema["$defs"] = schema.pop("definitions")

        for key, value in list(schema.items()):
            if key == "$ref" and isinstance(value, str) and value.startswith("#/definitions/"):
                schema[key] = "#/$defs/" + value[len("#/definitions/"):]

        for old, bound in (("exclusiveMinimum", "minimum"), ("exclusiveMaximum", "maximum")):
            if old in schema:
                if schema[old] is True and bound in schema:
                    schema[old] = schema.pop(bound)
                else:
                    schema.pop(old)

        items = schema.get("items")
        if isinstance(items, list):
            schema["prefixItems"] = schema.pop("items")
            for child in schema["prefixItems"]:
                migrate(child)
            if "additionalItems" in schema:
                schema["items"] = schema.pop("additionalItems")
                migrate(schema["items"])
        else:
            if isinstance(items, dict):
                migrate(items)
            if "additionalItems" in schema:
                schema.pop("additionalItems")

        for key in ("properties", "patternProperties", "$defs"):
            value = schema.get(key)
            if isinstance(value, dict):
                for child in value.values():
                    migrate(child)

        additional = schema.get("additionalProperties")
        if isinstance(additional, dict):
            migrate(additional)

        if isinstance(schema.get("not"), dict):
            migrate(schema["not"])

        for key in ("allOf", "anyOf", "oneOf"):
            value = schema.get(key)
            if isinstance(value, list):
                for child in value:
                    migrate(child)

        dependencies = schema.pop("dependencies", None)
        if isinstance(dependencies, dict):
            required = {}
            dependent_schemas = {}
            for name, value in dependencies.items():
                if isinstance(value, list) and all(isinstance(item, str) for item in value):
                    required[name] = value
                else:
                    dependent_schemas[name] = value
                    migrate(value)
            if required:
                schema["dependentRequired"] = required
            if dependent_schemas:
                schema["dependentSchemas"] = dependent_schemas

    migrate(result)
    return result