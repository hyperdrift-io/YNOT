def transform(payload):
    import copy

    result = copy.deepcopy(payload)

    def migrate(schema, root=False):
        if not isinstance(schema, dict):
            return schema

        if root:
            schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"

        if "id" in schema:
            schema["$id"] = schema.pop("id")

        ref = schema.get("$ref")
        if isinstance(ref, str) and ref.startswith("#/definitions/"):
            schema["$ref"] = "#/$defs/" + ref[len("#/definitions/"):]

        definitions = schema.pop("definitions", None)
        if isinstance(definitions, dict):
            schema["$defs"] = definitions

        for exclusive, bound in (
            ("exclusiveMinimum", "minimum"),
            ("exclusiveMaximum", "maximum"),
        ):
            if exclusive in schema:
                value = schema[exclusive]
                if value is True:
                    if bound in schema:
                        schema[exclusive] = schema.pop(bound)
                    else:
                        schema.pop(exclusive)
                elif value is False:
                    schema.pop(exclusive)

        items = schema.get("items")
        if isinstance(items, list):
            schema["prefixItems"] = items
            schema.pop("items")
            if "additionalItems" in schema:
                schema["items"] = schema.pop("additionalItems")
        else:
            schema.pop("additionalItems", None)

        dependencies = schema.pop("dependencies", None)
        required = {}
        dependent_schemas = {}
        if isinstance(dependencies, dict):
            for key, value in dependencies.items():
                if isinstance(value, list) and all(isinstance(item, str) for item in value):
                    required[key] = value
                else:
                    dependent_schemas[key] = value
        if required:
            schema["dependentRequired"] = required
        if dependent_schemas:
            schema["dependentSchemas"] = dependent_schemas

        def migrate_map(key):
            mapping = schema.get(key)
            if isinstance(mapping, dict):
                for name, value in mapping.items():
                    mapping[name] = migrate(value)

        for key in ("properties", "patternProperties", "$defs"):
            migrate_map(key)

        if isinstance(schema.get("items"), dict):
            schema["items"] = migrate(schema["items"])
        if isinstance(schema.get("prefixItems"), list):
            schema["prefixItems"] = [migrate(value) for value in schema["prefixItems"]]
        for key in ("additionalItems", "additionalProperties", "not"):
            if isinstance(schema.get(key), dict):
                schema[key] = migrate(schema[key])
        for key in ("allOf", "anyOf", "oneOf"):
            if isinstance(schema.get(key), list):
                schema[key] = [migrate(value) for value in schema[key]]
        for value in dependent_schemas.values():
            migrate(value)

        return schema

    return migrate(result, root=True)