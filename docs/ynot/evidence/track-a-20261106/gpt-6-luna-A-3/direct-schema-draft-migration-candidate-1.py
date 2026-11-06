def transform(payload):
    import copy

    result = copy.deepcopy(payload)
    result["$schema"] = "https://json-schema.org/draft/2020-12/schema"

    def visit(schema):
        if not isinstance(schema, dict):
            return

        if "id" in schema:
            schema["$id"] = schema.pop("id")

        if "definitions" in schema:
            schema["$defs"] = schema.pop("definitions")

        ref = schema.get("$ref")
        if isinstance(ref, str) and ref.startswith("#/definitions/"):
            schema["$ref"] = "#/$defs/" + ref[len("#/definitions/"):]

        for exclusive, bound in (("exclusiveMinimum", "minimum"), ("exclusiveMaximum", "maximum")):
            if schema.get(exclusive) is True:
                if bound in schema:
                    schema[exclusive] = schema.pop(bound)
                else:
                    schema.pop(exclusive)
            elif schema.get(exclusive) is False:
                schema.pop(exclusive)

        items = schema.get("items")
        if isinstance(items, list):
            schema["prefixItems"] = schema.pop("items")
            if "additionalItems" in schema:
                schema["items"] = schema.pop("additionalItems")
        else:
            schema.pop("additionalItems", None)

        dependencies = schema.pop("dependencies", None)
        if isinstance(dependencies, dict):
            required = {}
            dependent_schemas = {}
            for key, value in dependencies.items():
                if isinstance(value, list) and all(isinstance(item, str) for item in value):
                    required[key] = value
                else:
                    dependent_schemas[key] = value
            if required:
                schema["dependentRequired"] = required
            if dependent_schemas:
                schema["dependentSchemas"] = dependent_schemas

        for keyword in ("properties", "patternProperties", "$defs"):
            value = schema.get(keyword)
            if isinstance(value, dict):
                for child in value.values():
                    visit(child)

        for keyword in ("items", "not", "additionalItems", "additionalProperties"):
            value = schema.get(keyword)
            if isinstance(value, dict):
                visit(value)
            elif keyword == "items" and isinstance(value, list):
                for child in value:
                    visit(child)

        for keyword in ("allOf", "anyOf", "oneOf"):
            value = schema.get(keyword)
            if isinstance(value, list):
                for child in value:
                    visit(child)

        for keyword in ("dependentSchemas",):
            value = schema.get(keyword)
            if isinstance(value, dict):
                for child in value.values():
                    visit(child)

    visit(result)
    return result