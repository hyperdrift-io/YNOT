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
            definitions = schema.pop("definitions")
            schema["$defs"] = definitions
            if isinstance(definitions, dict):
                for child in definitions.values():
                    visit(child)

        for key in ("properties", "patternProperties"):
            children = schema.get(key)
            if isinstance(children, dict):
                for child in children.values():
                    visit(child)

        if "$ref" in schema and isinstance(schema["$ref"], str):
            ref = schema["$ref"]
            if ref.startswith("#/definitions/"):
                schema["$ref"] = "#/$defs/" + ref[len("#/definitions/"):]

        for bound, limit in (("exclusiveMinimum", "minimum"), ("exclusiveMaximum", "maximum")):
            if bound in schema and isinstance(schema[bound], bool):
                if schema[bound] is True and limit in schema:
                    schema[bound] = schema.pop(limit)
                else:
                    schema.pop(bound)

        items = schema.get("items")
        if isinstance(items, list):
            schema["prefixItems"] = items
            for child in items:
                visit(child)
            schema.pop("items")
            if "additionalItems" in schema:
                schema["items"] = schema.pop("additionalItems")
                if isinstance(schema["items"], dict):
                    visit(schema["items"])
        else:
            if isinstance(items, dict):
                visit(items)
            if "additionalItems" in schema:
                schema.pop("additionalItems")

        for key in ("additionalProperties", "not"):
            child = schema.get(key)
            if isinstance(child, dict):
                visit(child)

        for key in ("allOf", "anyOf", "oneOf"):
            children = schema.get(key)
            if isinstance(children, list):
                for child in children:
                    visit(child)

        dependencies = schema.pop("dependencies", None)
        if isinstance(dependencies, dict):
            required = {}
            dependent_schemas = {}
            for name, value in dependencies.items():
                if isinstance(value, list) and all(isinstance(item, str) for item in value):
                    required[name] = value
                else:
                    dependent_schemas[name] = value
                    visit(value)
            if required:
                schema["dependentRequired"] = required
            if dependent_schemas:
                schema["dependentSchemas"] = dependent_schemas

    visit(result)
    return result