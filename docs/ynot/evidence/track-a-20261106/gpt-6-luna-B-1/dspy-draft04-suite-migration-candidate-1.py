def transform(payload):
    import copy

    document = copy.deepcopy(payload)
    draft_uri = "https://json-schema.org/draft/2020-12/schema"

    def migrate(schema, root=False):
        if not isinstance(schema, dict):
            return schema

        if root:
            schema["$schema"] = draft_uri

        if "id" in schema:
            schema["$id"] = schema.pop("id")

        if "definitions" in schema:
            definitions = schema.pop("definitions")
            schema["$defs"] = definitions

        ref = schema.get("$ref")
        if isinstance(ref, str) and ref.startswith("#/definitions/"):
            schema["$ref"] = "#/$defs/" + ref[len("#/definitions/"):]

        for keyword in ("exclusiveMinimum", "exclusiveMaximum"):
            bound = "minimum" if keyword == "exclusiveMinimum" else "maximum"
            if schema.get(keyword) is True and bound in schema:
                schema[keyword] = schema.pop(bound)
            elif keyword in schema:
                schema.pop(keyword)

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
            subschemas = schema.get(keyword)
            if isinstance(subschemas, dict):
                for value in subschemas.values():
                    migrate(value)

        for keyword in ("items", "prefixItems", "additionalItems", "not"):
            value = schema.get(keyword)
            if isinstance(value, list):
                for item in value:
                    migrate(item)
            elif isinstance(value, dict):
                migrate(value)

        value = schema.get("additionalProperties")
        if isinstance(value, dict):
            migrate(value)

        for keyword in ("allOf", "anyOf", "oneOf"):
            values = schema.get(keyword)
            if isinstance(values, list):
                for value in values:
                    migrate(value)

        dependent_schemas = schema.get("dependentSchemas")
        if isinstance(dependent_schemas, dict):
            for value in dependent_schemas.values():
                migrate(value)

        return schema

    return migrate(document, root=True)