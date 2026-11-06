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

        if "definitions" in schema:
            schema["$defs"] = schema.pop("definitions")

        ref = schema.get("$ref")
        if isinstance(ref, str) and ref.startswith("#/definitions/"):
            schema["$ref"] = "#/$defs/" + ref[len("#/definitions/"):]

        for bound, exclusive in (
            ("minimum", "exclusiveMinimum"),
            ("maximum", "exclusiveMaximum"),
        ):
            if exclusive in schema:
                flag = schema[exclusive]
                if flag is True:
                    if bound in schema:
                        schema[exclusive] = schema.pop(bound)
                    else:
                        schema.pop(exclusive)
                elif flag is False:
                    schema.pop(exclusive)

        if isinstance(schema.get("items"), list):
            schema["prefixItems"] = schema.pop("items")
            if "additionalItems" in schema:
                schema["items"] = schema.pop("additionalItems")
        else:
            schema.pop("additionalItems", None)

        dependencies = schema.pop("dependencies", None)
        if isinstance(dependencies, dict):
            dependent_required = {}
            dependent_schemas = {}
            for name, value in dependencies.items():
                if isinstance(value, list) and all(isinstance(item, str) for item in value):
                    dependent_required[name] = value
                else:
                    dependent_schemas[name] = value
            if dependent_required:
                schema["dependentRequired"] = dependent_required
            if dependent_schemas:
                schema["dependentSchemas"] = dependent_schemas

        for keyword in ("properties", "patternProperties", "$defs"):
            mapping = schema.get(keyword)
            if isinstance(mapping, dict):
                for subschema in mapping.values():
                    migrate(subschema)

        dependent_schemas = schema.get("dependentSchemas")
        if isinstance(dependent_schemas, dict):
            for subschema in dependent_schemas.values():
                migrate(subschema)

        items = schema.get("items")
        if isinstance(items, dict):
            migrate(items)

        prefix_items = schema.get("prefixItems")
        if isinstance(prefix_items, list):
            for subschema in prefix_items:
                migrate(subschema)

        for keyword in ("additionalItems", "additionalProperties", "not"):
            subschema = schema.get(keyword)
            if isinstance(subschema, dict):
                migrate(subschema)

        for keyword in ("allOf", "anyOf", "oneOf"):
            subschemas = schema.get(keyword)
            if isinstance(subschemas, list):
                for subschema in subschemas:
                    migrate(subschema)

        return schema

    return migrate(result, root=True)