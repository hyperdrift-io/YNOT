def transform(payload):
    import copy

    result = copy.deepcopy(payload)
    target_schema = "https://json-schema.org/draft/2020-12/schema"
    schema_maps = ("properties", "patternProperties", "definitions", "$defs")
    schema_arrays = ("allOf", "anyOf", "oneOf")

    def visit(schema, root=False):
        if not isinstance(schema, dict):
            return
        if root:
            schema["$schema"] = target_schema
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
                    schema.pop(exclusive, None)
            elif schema.get(exclusive) is False:
                schema.pop(exclusive, None)

        items = schema.get("items")
        if isinstance(items, list):
            schema["prefixItems"] = schema.pop("items")
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
                elif isinstance(value, dict) or isinstance(value, bool):
                    dependent_schemas[name] = value
            if required:
                schema["dependentRequired"] = required
            if dependent_schemas:
                schema["dependentSchemas"] = dependent_schemas

        for key in schema_maps:
            mapping = schema.get(key)
            if isinstance(mapping, dict):
                for child in mapping.values():
                    visit(child)
        items = schema.get("items")
        if isinstance(items, list):
            for child in items:
                visit(child)
        else:
            visit(items)
        for key in ("additionalItems", "additionalProperties", "not"):
            child = schema.get(key)
            if isinstance(child, dict) or isinstance(child, bool):
                visit(child)
        for key in schema_arrays:
            children = schema.get(key)
            if isinstance(children, list):
                for child in children:
                    visit(child)
        dependencies = schema.get("dependentSchemas")
        if isinstance(dependencies, dict):
            for child in dependencies.values():
                visit(child)

    visit(result, True)
    return result