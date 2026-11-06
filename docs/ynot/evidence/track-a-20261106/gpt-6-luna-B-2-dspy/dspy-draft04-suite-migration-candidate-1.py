def transform(payload):
    import copy

    if not isinstance(payload, dict):
        raise TypeError("payload must be a JSON Schema object")

    result = copy.deepcopy(payload)
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

        for old, bound in (("exclusiveMinimum", "minimum"),
                           ("exclusiveMaximum", "maximum")):
            if old in schema:
                exclusive = schema[old]
                if exclusive is True and bound in schema:
                    schema[old] = schema.pop(bound)
                else:
                    schema.pop(old)

        items = schema.get("items")
        if isinstance(items, list):
            schema["prefixItems"] = items
            if "items" in schema:
                del schema["items"]
            if "additionalItems" in schema:
                schema["items"] = schema.pop("additionalItems")
        else:
            schema.pop("additionalItems", None)

        dependencies = schema.pop("dependencies", None)
        if isinstance(dependencies, dict):
            required = {}
            dependent_schemas = {}
            for name, value in dependencies.items():
                if isinstance(value, list) and all(isinstance(x, str) for x in value):
                    required[name] = value
                else:
                    dependent_schemas[name] = value
                    migrate(value)
            if required:
                schema["dependentRequired"] = required
            if dependent_schemas:
                schema["dependentSchemas"] = dependent_schemas

        for keyword in ("properties", "patternProperties", "$defs"):
            members = schema.get(keyword)
            if isinstance(members, dict):
                for child in members.values():
                    migrate(child)

        for keyword in ("items", "additionalItems", "additionalProperties", "not"):
            child = schema.get(keyword)
            if isinstance(child, dict):
                migrate(child)

        for keyword in ("prefixItems", "allOf", "anyOf", "oneOf"):
            children = schema.get(keyword)
            if isinstance(children, list):
                for child in children:
                    migrate(child)

    migrate(result)
    return result