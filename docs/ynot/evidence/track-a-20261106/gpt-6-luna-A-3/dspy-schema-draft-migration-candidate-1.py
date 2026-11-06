def transform(payload):
    import copy

    schema_uri = "https://json-schema.org/draft/2020-12/schema"
    result = copy.deepcopy(payload)

    def migrate(schema, root=False):
        if not isinstance(schema, dict):
            return

        if root:
            schema["$schema"] = schema_uri

        if "id" in schema:
            schema["$id"] = schema.pop("id")

        if "definitions" in schema:
            schema["$defs"] = schema.pop("definitions")

        ref = schema.get("$ref")
        if isinstance(ref, str) and ref.startswith("#/definitions/"):
            schema["$ref"] = "#/$defs/" + ref[len("#/definitions/"):]

        for exclusive, bound in (
            ("exclusiveMinimum", "minimum"),
            ("exclusiveMaximum", "maximum"),
        ):
            if exclusive in schema:
                value = schema[exclusive]
                if value is True and bound in schema:
                    schema[exclusive] = schema.pop(bound)
                elif value is False or value is True:
                    schema.pop(exclusive)

        if "items" in schema and isinstance(schema["items"], list):
            schema["prefixItems"] = schema.pop("items")
            if "additionalItems" in schema:
                schema["items"] = schema.pop("additionalItems")
        else:
            schema.pop("additionalItems", None)

        if "dependencies" in schema:
            dependent_required = {}
            dependent_schemas = {}
            dependencies = schema.pop("dependencies")
            if isinstance(dependencies, dict):
                for key, value in dependencies.items():
                    if isinstance(value, list) and all(isinstance(item, str) for item in value):
                        dependent_required[key] = value
                    else:
                        dependent_schemas[key] = value
            if dependent_required:
                schema["dependentRequired"] = dependent_required
            if dependent_schemas:
                schema["dependentSchemas"] = dependent_schemas

        def walk(value):
            if isinstance(value, dict):
                migrate(value)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        migrate(item)

        for keyword in ("$defs", "properties", "patternProperties"):
            value = schema.get(keyword)
            if isinstance(value, dict):
                for child in value.values():
                    walk(child)

        for keyword in ("items", "prefixItems", "additionalItems", "not",
                        "additionalProperties", "allOf", "anyOf", "oneOf",
                        "dependentSchemas"):
            if keyword not in schema:
                continue
            value = schema[keyword]
            if keyword in ("allOf", "anyOf", "oneOf", "prefixItems"):
                walk(value)
            elif isinstance(value, dict):
                walk(value)

        # Legacy dependencies may contain schemas that were moved above.
        # New dependentSchemas are traversed by the branch above.

    migrate(result, root=True)
    return result