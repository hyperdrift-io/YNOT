def transform(payload):
    import copy

    result = copy.deepcopy(payload)
    if not isinstance(result, dict):
        return result

    result["$schema"] = "https://json-schema.org/draft/2020-12/schema"

    def visit(schema):
        if not isinstance(schema, dict):
            return

        if "id" in schema:
            schema["$id"] = schema.pop("id")

        if "definitions" in schema:
            definitions = schema.pop("definitions")
            schema["$defs"] = definitions
            if isinstance(definitions, dict):
                for child in definitions.values():
                    visit(child)

        ref = schema.get("$ref")
        if isinstance(ref, str) and ref.startswith("#/definitions/"):
            schema["$ref"] = "#/$defs/" + ref[len("#/definitions/"):]

        for exclusive, bound in (
            ("exclusiveMinimum", "minimum"),
            ("exclusiveMaximum", "maximum"),
        ):
            if exclusive in schema:
                value = schema.pop(exclusive)
                if value is True and bound in schema:
                    schema[exclusive] = schema.pop(bound)
                elif value is not True:
                    # False and other non-true values are removed.
                    pass

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
            required = {}
            dependent_schemas = {}
            for key, value in dependencies.items():
                if isinstance(value, list) and all(isinstance(x, str) for x in value):
                    required[key] = value
                else:
                    dependent_schemas[key] = value
                    visit(value)
            if required:
                schema["dependentRequired"] = required
            if dependent_schemas:
                schema["dependentSchemas"] = dependent_schemas

        for key in ("properties", "patternProperties", "additionalProperties", "not"):
            child = schema.get(key)
            if key in ("properties", "patternProperties") and isinstance(child, dict):
                for value in child.values():
                    visit(value)
            elif isinstance(child, dict):
                visit(child)

        for key in ("items", "additionalItems"):
            child = schema.get(key)
            if isinstance(child, dict):
                visit(child)

        for key in ("allOf", "anyOf", "oneOf"):
            children = schema.get(key)
            if isinstance(children, list):
                for child in children:
                    visit(child)

    visit(result)
    return result