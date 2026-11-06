def transform(payload):
    import copy

    result = copy.deepcopy(payload)

    def visit(schema, root=False):
        if not isinstance(schema, dict):
            return

        if root:
            schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"

        if "id" in schema:
            schema["$id"] = schema.pop("id")

        if "definitions" in schema:
            schema["$defs"] = schema.pop("definitions")

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
                if isinstance(value, list) and all(isinstance(entry, str) for entry in value):
                    dependent_required[name] = value
                else:
                    dependent_schemas[name] = value
            if dependent_required:
                schema["dependentRequired"] = dependent_required
            if dependent_schemas:
                schema["dependentSchemas"] = dependent_schemas

        ref = schema.get("$ref")
        if isinstance(ref, str) and ref.startswith("#/definitions/"):
            schema["$ref"] = "#/$defs/" + ref[len("#/definitions/"):]

        for key in ("properties", "patternProperties", "$defs"):
            children = schema.get(key)
            if isinstance(children, dict):
                for child in children.values():
                    visit(child)

        for key in ("items", "prefixItems", "additionalItems", "not"):
            child = schema.get(key)
            if isinstance(child, list):
                for member in child:
                    visit(member)
            else:
                visit(child)

        additional = schema.get("additionalProperties")
        if isinstance(additional, dict):
            visit(additional)

        for key in ("allOf", "anyOf", "oneOf"):
            children = schema.get(key)
            if isinstance(children, list):
                for child in children:
                    visit(child)

        dependent_schemas = schema.get("dependentSchemas")
        if isinstance(dependent_schemas, dict):
            for child in dependent_schemas.values():
                visit(child)

    visit(result, root=True)
    return result