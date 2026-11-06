def transform(payload):
    import copy

    result = copy.deepcopy(payload)
    draft_uri = "https://json-schema.org/draft/2020-12/schema"

    def walk(schema, is_root=False):
        if not isinstance(schema, dict):
            return

        if is_root:
            schema["$schema"] = draft_uri

        if "id" in schema:
            schema["$id"] = schema.pop("id")

        if "$ref" in schema and isinstance(schema["$ref"], str):
            ref = schema["$ref"]
            if ref.startswith("#/definitions/"):
                schema["$ref"] = "#/$defs/" + ref[len("#/definitions/"):]

        if "definitions" in schema:
            definitions = schema.pop("definitions")
            if "$defs" in schema and isinstance(schema["$defs"], dict) and isinstance(definitions, dict):
                schema["$defs"] = {**definitions, **schema["$defs"]}
            else:
                schema["$defs"] = definitions

        for exclusive, inclusive in (("exclusiveMinimum", "minimum"), ("exclusiveMaximum", "maximum")):
            if exclusive in schema:
                if schema[exclusive] is True and inclusive in schema:
                    schema[exclusive] = schema.pop(inclusive)
                else:
                    schema.pop(exclusive)

        if isinstance(schema.get("items"), list):
            schema["prefixItems"] = schema.pop("items")
            if "additionalItems" in schema:
                schema["items"] = schema.pop("additionalItems")
        else:
            schema.pop("additionalItems", None)

        dependencies = schema.pop("dependencies", None)
        dependent_required = {}
        dependent_schemas = {}
        if isinstance(dependencies, dict):
            for key, value in dependencies.items():
                if isinstance(value, list) and all(isinstance(item, str) for item in value):
                    dependent_required[key] = value
                else:
                    dependent_schemas[key] = value
            if dependent_required:
                schema["dependentRequired"] = dependent_required
            if dependent_schemas:
                schema["dependentSchemas"] = dependent_schemas

        for keyword in ("properties", "patternProperties"):
            value = schema.get(keyword)
            if isinstance(value, dict):
                for child in value.values():
                    walk(child)

        defs = schema.get("$defs")
        if isinstance(defs, dict):
            for child in defs.values():
                walk(child)

        for keyword in ("items", "additionalItems", "not"):
            child = schema.get(keyword)
            if isinstance(child, dict):
                walk(child)

        for keyword in ("allOf", "anyOf", "oneOf", "prefixItems"):
            value = schema.get(keyword)
            if isinstance(value, list):
                for child in value:
                    walk(child)

        additional = schema.get("additionalProperties")
        if isinstance(additional, dict):
            walk(additional)

        dependent_schemas = schema.get("dependentSchemas")
        if isinstance(dependent_schemas, dict):
            for child in dependent_schemas.values():
                walk(child)

    walk(result, True)
    return result