def transform(payload):
    import copy

    document = copy.deepcopy(payload)
    draft_uri = "https://json-schema.org/draft/2020-12/schema"

    def migrate(schema, is_root=False):
        if not isinstance(schema, dict):
            return schema

        if is_root or "$schema" in schema:
            schema["$schema"] = draft_uri

        if "id" in schema:
            schema["$id"] = schema.pop("id")

        if "definitions" in schema:
            schema["$defs"] = schema.pop("definitions")

        ref = schema.get("$ref")
        if isinstance(ref, str) and ref.startswith("#/definitions/"):
            schema["$ref"] = "#/$defs/" + ref[len("#/definitions/"):]

        for exclusive, bound in (("exclusiveMinimum", "minimum"),
                                  ("exclusiveMaximum", "maximum")):
            if exclusive in schema:
                value = schema[exclusive]
                if value is True and bound in schema:
                    schema[exclusive] = schema.pop(bound)
                elif value is False or value is True:
                    schema.pop(exclusive)

        if "items" in schema and isinstance(schema["items"], list):
            schema["prefixItems"] = schema.pop("items")
            if "additionalItems" in schema:
                schema["items"] = schema.pop("additionalItems")
        else:
            schema.pop("additionalItems", None)

        if "dependencies" in schema:
            required = {}
            dependent_schemas = {}
            for key, value in schema.pop("dependencies").items():
                if isinstance(value, list) and all(isinstance(item, str) for item in value):
                    required[key] = value
                else:
                    dependent_schemas[key] = value
            if required:
                schema["dependentRequired"] = required
            if dependent_schemas:
                schema["dependentSchemas"] = dependent_schemas

        for keyword in ("properties", "patternProperties", "definitions", "$defs"):
            mapping = schema.get(keyword)
            if isinstance(mapping, dict):
                for value in mapping.values():
                    migrate(value)

        for keyword in ("items", "prefixItems", "additionalItems"):
            value = schema.get(keyword)
            if isinstance(value, dict):
                migrate(value)
            elif isinstance(value, list):
                for member in value:
                    migrate(member)

        for keyword in ("additionalProperties", "not"):
            value = schema.get(keyword)
            if isinstance(value, dict):
                migrate(value)

        for keyword in ("allOf", "anyOf", "oneOf"):
            value = schema.get(keyword)
            if isinstance(value, list):
                for member in value:
                    migrate(member)

        dependent = schema.get("dependencies")
        if isinstance(dependent, dict):
            for value in dependent.values():
                if isinstance(value, dict):
                    migrate(value)

        dependent_schemas = schema.get("dependentSchemas")
        if isinstance(dependent_schemas, dict):
            for value in dependent_schemas.values():
                migrate(value)

        return schema

    return migrate(document, True)