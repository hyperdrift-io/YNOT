def transform(payload):
    result = __import__("copy").deepcopy(payload)
    if not isinstance(result, dict):
        return result

    result["$schema"] = "https://json-schema.org/draft/2020-12/schema"

    def migrate(schema):
        if not isinstance(schema, dict):
            return

        if "id" in schema:
            schema["$id"] = schema.pop("id")
        if "definitions" in schema:
            schema["$defs"] = schema.pop("definitions")

        ref = schema.get("$ref")
        if isinstance(ref, str) and ref.startswith("#/definitions/"):
            schema["$ref"] = "#/$defs/" + ref[len("#/definitions/"):]

        for exclusive, bound in (
            ("exclusiveMinimum", "minimum"),
            ("exclusiveMaximum", "maximum"),
        ):
            if exclusive in schema:
                value = schema[exclusive]
                if value is True and bound in schema:
                    schema[exclusive] = schema.pop(bound)
                elif value is True or value is False:
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
                    migrate(child)

        for keyword in ("items", "prefixItems", "not", "allOf", "anyOf", "oneOf"):
            value = schema.get(keyword)
            if isinstance(value, list):
                for child in value:
                    migrate(child)
            elif isinstance(value, dict):
                migrate(value)

        for keyword in ("additionalItems", "additionalProperties"):
            value = schema.get(keyword)
            if isinstance(value, dict):
                migrate(value)

        dependent_schemas = schema.get("dependentSchemas")
        if isinstance(dependent_schemas, dict):
            for child in dependent_schemas.values():
                migrate(child)

    migrate(result)
    return result