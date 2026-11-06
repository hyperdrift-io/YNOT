def transform(payload):
    import copy

    result = copy.deepcopy(payload)
    target_dialect = "https://json-schema.org/draft/2020-12/schema"

    def is_schema(value):
        return isinstance(value, (dict, bool))

    def walk(schema, root=False):
        if isinstance(schema, bool):
            return schema
        if not isinstance(schema, dict):
            return schema

        if root:
            schema["$schema"] = target_dialect
        if "id" in schema:
            schema["$id"] = schema.pop("id")

        if "definitions" in schema:
            schema["$defs"] = schema.pop("definitions")
            definitions = schema["$defs"]
            if isinstance(definitions, dict):
                for value in definitions.values():
                    if is_schema(value):
                        walk(value)

        ref = schema.get("$ref")
        if isinstance(ref, str) and ref.startswith("#/definitions/"):
            schema["$ref"] = "#/$defs/" + ref[len("#/definitions/"):]

        for exclusive, bound in (("exclusiveMinimum", "minimum"), ("exclusiveMaximum", "maximum")):
            if exclusive in schema:
                if schema[exclusive] is True and bound in schema:
                    schema[exclusive] = schema.pop(bound)
                else:
                    schema.pop(exclusive)

        items = schema.get("items")
        if isinstance(items, list):
            schema["prefixItems"] = schema.pop("items")
            if "additionalItems" in schema:
                schema["items"] = schema.pop("additionalItems")
            for value in schema["prefixItems"]:
                if is_schema(value):
                    walk(value)
        else:
            schema.pop("additionalItems", None)
            if is_schema(items):
                walk(items)

        dependencies = schema.pop("dependencies", None)
        if isinstance(dependencies, dict):
            required, dependent_schemas = {}, {}
            for key, value in dependencies.items():
                if isinstance(value, list) and all(isinstance(item, str) for item in value):
                    required[key] = value
                else:
                    dependent_schemas[key] = value
                    if is_schema(value):
                        walk(value)
            if required:
                schema["dependentRequired"] = required
            if dependent_schemas:
                schema["dependentSchemas"] = dependent_schemas

        for keyword in ("properties", "patternProperties"):
            members = schema.get(keyword)
            if isinstance(members, dict):
                for value in members.values():
                    if is_schema(value):
                        walk(value)

        for keyword in ("additionalProperties", "not"):
            value = schema.get(keyword)
            if is_schema(value):
                walk(value)

        for keyword in ("allOf", "anyOf", "oneOf"):
            members = schema.get(keyword)
            if isinstance(members, list):
                for value in members:
                    if is_schema(value):
                        walk(value)

        return schema

    return walk(result, root=True)
