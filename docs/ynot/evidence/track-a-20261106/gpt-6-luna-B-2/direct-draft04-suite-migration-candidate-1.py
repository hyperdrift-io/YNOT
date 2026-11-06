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
        if isinstance(schema.get("$ref"), str) and schema["$ref"].startswith("#/definitions/"):
            schema["$ref"] = "#/$defs/" + schema["$ref"][len("#/definitions/"):]

        for old, bound in (("exclusiveMinimum", "minimum"), ("exclusiveMaximum", "maximum")):
            if old in schema and isinstance(schema[old], bool):
                if schema[old] and bound in schema:
                    schema[old] = schema.pop(bound)
                else:
                    schema.pop(old)

        items = schema.get("items")
        if isinstance(items, list):
            schema["prefixItems"] = schema.pop("items")
            if "additionalItems" in schema:
                schema["items"] = schema.pop("additionalItems")
        else:
            schema.pop("additionalItems", None)

        dependencies = schema.pop("dependencies", None)
        if isinstance(dependencies, dict):
            required, dependent_schemas = {}, {}
            for key, value in dependencies.items():
                if isinstance(value, list) and all(isinstance(item, str) for item in value):
                    required[key] = value
                else:
                    dependent_schemas[key] = value
                    visit(value)
            if required:
                schema["dependentRequired"] = required
            if dependent_schemas:
                schema["dependentSchemas"] = dependent_schemas

        for keyword in ("properties", "patternProperties", "$defs"):
            value = schema.get(keyword)
            if isinstance(value, dict):
                for child in value.values():
                    visit(child)

        items = schema.get("items")
        if isinstance(items, list):
            for child in items:
                visit(child)
        else:
            visit(items)
        for keyword in ("additionalItems", "additionalProperties", "not"):
            visit(schema.get(keyword))
        for keyword in ("allOf", "anyOf", "oneOf"):
            value = schema.get(keyword)
            if isinstance(value, list):
                for child in value:
                    visit(child)

    visit(result)
    return result