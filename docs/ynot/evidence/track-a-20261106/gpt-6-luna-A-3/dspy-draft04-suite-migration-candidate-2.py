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

        for exclusive, inclusive in (
            ("exclusiveMinimum", "minimum"),
            ("exclusiveMaximum", "maximum"),
        ):
            if exclusive in schema:
                value = schema.pop(exclusive)
                if value is True and inclusive in schema:
                    schema[exclusive] = schema.pop(inclusive)

        items = schema.get("items")
        if isinstance(items, list):
            schema["prefixItems"] = items
            schema.pop("items")
            if "additionalItems" in schema:
                schema["items"] = schema.pop("additionalItems")
        else:
            schema.pop("additionalItems", None)

        dependencies = schema.pop("dependencies", None)
        if isinstance(dependencies, dict):
            dependent_required = {}
            dependent_schemas = {}
            for key, value in dependencies.items():
                if isinstance(value, list) and all(isinstance(item, str) for item in value):
                    dependent_required[key] = value
                else:
                    dependent_schemas[key] = value
                    migrate(value)
            if dependent_required:
                schema["dependentRequired"] = dependent_required
            if dependent_schemas:
                schema["dependentSchemas"] = dependent_schemas

        for keyword in ("properties", "patternProperties", "definitions"):
            mapping = schema.get(keyword)
            if isinstance(mapping, dict):
                for child in mapping.values():
                    migrate(child)

        for keyword in ("items", "prefixItems", "additionalItems", "not"):
            child = schema.get(keyword)
            if isinstance(child, list):
                for entry in child:
                    migrate(entry)
            else:
                migrate(child)

        child = schema.get("additionalProperties")
        if isinstance(child, dict):
            migrate(child)

        for keyword in ("allOf", "anyOf", "oneOf"):
            children = schema.get(keyword)
            if isinstance(children, list):
                for child in children:
                    migrate(child)

        return schema

    return migrate(result, root=True)