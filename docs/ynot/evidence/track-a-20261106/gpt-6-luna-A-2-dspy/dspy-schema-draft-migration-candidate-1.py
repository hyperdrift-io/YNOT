def transform(payload):
    import copy

    result = copy.deepcopy(payload)
    draft_uri = "https://json-schema.org/draft/2020-12/schema"

    def migrate(schema, is_root=False):
        if not isinstance(schema, dict):
            return

        if is_root:
            schema["$schema"] = draft_uri

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
                value = schema[exclusive]
                if value is True and inclusive in schema:
                    schema[exclusive] = schema.pop(inclusive)
                elif value is True or value is False:
                    schema.pop(exclusive)

        if "items" in schema and isinstance(schema["items"], list):
            schema["prefixItems"] = schema.pop("items")
            if "additionalItems" in schema:
                schema["items"] = schema.pop("additionalItems")
        else:
            schema.pop("additionalItems", None)

        if "dependencies" in schema:
            required = {}
            dependent_schemas = {}
            for key, value in schema.pop("dependencies").items():
                if isinstance(value, list) and all(isinstance(item, str) for item in value):
                    required[key] = value
                else:
                    dependent_schemas[key] = value
            if required:
                schema["dependentRequired"] = required
            if dependent_schemas:
                schema["dependentSchemas"] = dependent_schemas

        for keyword in ("properties", "patternProperties", "$defs"):
            mapping = schema.get(keyword)
            if isinstance(mapping, dict):
                for child in mapping.values():
                    migrate(child)

        dependencies = schema.get("dependentSchemas")
        if isinstance(dependencies, dict):
            for child in dependencies.values():
                migrate(child)

        items = schema.get("items")
        if isinstance(items, dict):
            migrate(items)
        prefix_items = schema.get("prefixItems")
        if isinstance(prefix_items, list):
            for child in prefix_items:
                migrate(child)

        for keyword in ("additionalProperties", "not"):
            child = schema.get(keyword)
            if isinstance(child, dict):
                migrate(child)

        for keyword in ("allOf", "anyOf", "oneOf"):
            children = schema.get(keyword)
            if isinstance(children, list):
                for child in children:
                    migrate(child)

    migrate(result, is_root=True)
    return result