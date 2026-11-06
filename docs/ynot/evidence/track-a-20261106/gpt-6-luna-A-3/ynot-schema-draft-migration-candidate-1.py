def transform(payload):
    import copy

    result = copy.deepcopy(payload)
    result["$schema"] = "https://json-schema.org/draft/2020-12/schema"

    def migrate(schema):
        if not isinstance(schema, dict):
            return

        if "id" in schema:
            schema["$id"] = schema.pop("id")

        if "definitions" in schema:
            schema["$defs"] = schema.pop("definitions")

        for key, value in list(schema.items()):
            if key == "$ref" and isinstance(value, str) and value.startswith("#/definitions/"):
                schema[key] = "#/$defs/" + value[len("#/definitions/"):]

        for exclusive, inclusive in (("exclusiveMinimum", "minimum"), ("exclusiveMaximum", "maximum")):
            if exclusive in schema and isinstance(schema[exclusive], bool):
                if schema[exclusive] is True and inclusive in schema:
                    schema[exclusive] = schema.pop(inclusive)
                else:
                    schema.pop(exclusive)

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
            for name, value in dependencies.items():
                if isinstance(value, list) and all(isinstance(item, str) for item in value):
                    required[name] = value
                else:
                    dependent_schemas[name] = value
            if required:
                schema["dependentRequired"] = required
            if dependent_schemas:
                schema["dependentSchemas"] = dependent_schemas

        for key in ("properties", "patternProperties", "$defs", "definitions"):
            members = schema.get(key)
            if isinstance(members, dict):
                for child in members.values():
                    migrate(child)

        for key in ("items", "additionalItems", "additionalProperties", "not"):
            child = schema.get(key)
            if isinstance(child, dict):
                migrate(child)
            elif key == "items" and isinstance(child, list):
                for member in child:
                    migrate(member)

        for key in ("allOf", "anyOf", "oneOf"):
            members = schema.get(key)
            if isinstance(members, list):
                for child in members:
                    migrate(child)

        members = schema.get("dependentSchemas")
        if isinstance(members, dict):
            for child in members.values():
                migrate(child)

    migrate(result)
    return result