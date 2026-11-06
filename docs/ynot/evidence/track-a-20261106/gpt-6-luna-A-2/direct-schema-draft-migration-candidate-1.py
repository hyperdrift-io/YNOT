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

        if isinstance(schema.get("items"), list):
            schema["prefixItems"] = schema.pop("items")
            if "additionalItems" in schema:
                schema["items"] = schema.pop("additionalItems")
        else:
            schema.pop("additionalItems", None)

        dependencies = schema.pop("dependencies", None)
        if isinstance(dependencies, dict):
            required, dependent_schemas = {}, {}
            for name, value in dependencies.items():
                if isinstance(value, list) and all(isinstance(item, str) for item in value):
                    required[name] = value
                else:
                    dependent_schemas[name] = value
            if required:
                schema["dependentRequired"] = required
            if dependent_schemas:
                schema["dependentSchemas"] = dependent_schemas

        for keyword in ("properties", "patternProperties", "definitions", "additionalProperties"):
            value = schema.get(keyword)
            if isinstance(value, dict):
                for subschema in value.values():
                    visit(subschema)

        items = schema.get("items")
        if isinstance(items, dict):
            visit(items)
        elif isinstance(items, list):
            for subschema in items:
                visit(subschema)

        for keyword in ("additionalItems", "not"):
            visit(schema.get(keyword))

        for keyword in ("allOf", "anyOf", "oneOf"):
            value = schema.get(keyword)
            if isinstance(value, list):
                for subschema in value:
                    visit(subschema)

        dependent_schemas = schema.get("dependentSchemas")
        if isinstance(dependent_schemas, dict):
            for subschema in dependent_schemas.values():
                visit(subschema)

    visit(result)
    return result
