def transform(payload):
    import copy

    result = copy.deepcopy(payload)
    schema_uri = "https://json-schema.org/draft/2020-12/schema"

    def migrate(schema, is_root=False):
        if not isinstance(schema, dict):
            return

        if is_root:
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
            value = schema.get(exclusive)
            if value is True:
                if bound in schema:
                    schema[exclusive] = schema.pop(bound)
                else:
                    schema.pop(exclusive)
            elif value is False:
                schema.pop(exclusive)

        items = schema.get("items")
        if isinstance(items, list):
            schema["prefixItems"] = schema.pop("items")
            if "additionalItems" in schema:
                schema["items"] = schema.pop("additionalItems")
        else:
            schema.pop("additionalItems", None)

        dependent_required = {}
        dependent_schemas = {}
        dependencies = schema.pop("dependencies", None)
        if isinstance(dependencies, dict):
            for key, value in dependencies.items():
                if isinstance(value, list) and all(
                    isinstance(item, str) for item in value
                ):
                    dependent_required[key] = value
                else:
                    dependent_schemas[key] = value
        if dependent_required:
            schema["dependentRequired"] = dependent_required
        if dependent_schemas:
            schema["dependentSchemas"] = dependent_schemas

        for keyword in ("properties", "patternProperties", "definitions", "$defs"):
            children = schema.get(keyword)
            if isinstance(children, dict):
                for child in children.values():
                    migrate(child)

        items = schema.get("items")
        if isinstance(items, dict):
            migrate(items)
        elif isinstance(items, list):
            for child in items:
                migrate(child)

        additional_items = schema.get("additionalItems")
        if isinstance(additional_items, dict):
            migrate(additional_items)

        for keyword in ("additionalProperties", "not"):
            child = schema.get(keyword)
            if isinstance(child, dict):
                migrate(child)

        for keyword in ("allOf", "anyOf", "oneOf"):
            children = schema.get(keyword)
            if isinstance(children, list):
                for child in children:
                    migrate(child)

        children = schema.get("dependentSchemas")
        if isinstance(children, dict):
            for child in children.values():
                migrate(child)

    migrate(result, is_root=True)
    return result