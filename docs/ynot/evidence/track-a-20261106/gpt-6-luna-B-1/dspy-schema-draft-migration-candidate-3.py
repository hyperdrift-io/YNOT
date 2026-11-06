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

        if "definitions" in schema:
            schema["$defs"] = schema.pop("definitions")

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
            schema["prefixItems"] = [migrate(item) for item in items]
            schema.pop("items")
            if "additionalItems" in schema:
                schema["items"] = migrate(schema.pop("additionalItems"))
        else:
            if isinstance(items, dict):
                schema["items"] = migrate(items)
            schema.pop("additionalItems", None)

        for keyword in ("properties", "patternProperties", "$defs"):
            mapping = schema.get(keyword)
            if isinstance(mapping, dict):
                for name, value in list(mapping.items()):
                    mapping[name] = migrate(value)

        if isinstance(schema.get("additionalProperties"), dict):
            schema["additionalProperties"] = migrate(schema["additionalProperties"])

        if isinstance(schema.get("not"), dict):
            schema["not"] = migrate(schema["not"])

        for keyword in ("allOf", "anyOf", "oneOf"):
            if isinstance(schema.get(keyword), list):
                schema[keyword] = [migrate(item) for item in schema[keyword]]

        dependencies = schema.pop("dependencies", None)
        if isinstance(dependencies, dict):
            required = {}
            dependent_schemas = {}
            for name, value in dependencies.items():
                if isinstance(value, list) and all(isinstance(item, str) for item in value):
                    required[name] = value
                else:
                    dependent_schemas[name] = migrate(value)
            if required:
                schema["dependentRequired"] = required
            if dependent_schemas:
                schema["dependentSchemas"] = dependent_schemas

        return schema

    return migrate(result, root=True)