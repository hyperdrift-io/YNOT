def transform(payload):
    import copy

    result = copy.deepcopy(payload)
    target = "https://json-schema.org/draft/2020-12/schema"

    def visit(schema, root=False):
        if not isinstance(schema, dict):
            return
        if root:
            schema["$schema"] = target
        if "id" in schema:
            schema["$id"] = schema.pop("id")
        if "definitions" in schema:
            schema["$defs"] = schema.pop("definitions")
        for key, value in list(schema.items()):
            if key == "$ref" and isinstance(value, str) and value.startswith("#/definitions/"):
                schema[key] = "#/$defs/" + value[len("#/definitions/"):]

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
            required, dependent = {}, {}
            for name, value in dependencies.items():
                if isinstance(value, list) and all(isinstance(item, str) for item in value):
                    required[name] = value
                else:
                    dependent[name] = value
            if required:
                schema["dependentRequired"] = required
            if dependent:
                schema["dependentSchemas"] = dependent

        for key in ("properties", "patternProperties", "$defs"):
            value = schema.get(key)
            if isinstance(value, dict):
                for child in value.values():
                    visit(child)
        for key in ("items", "prefixItems", "additionalItems", "not", "additionalProperties"):
            value = schema.get(key)
            if isinstance(value, list):
                for child in value:
                    visit(child)
            elif isinstance(value, dict):
                visit(value)
        for key in ("allOf", "anyOf", "oneOf"):
            value = schema.get(key)
            if isinstance(value, list):
                for child in value:
                    visit(child)
        dependent = schema.get("dependentSchemas")
        if isinstance(dependent, dict):
            for child in dependent.values():
                visit(child)

    visit(result, True)
    return result