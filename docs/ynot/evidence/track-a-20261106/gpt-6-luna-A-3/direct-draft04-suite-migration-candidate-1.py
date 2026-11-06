def transform(payload):
    import copy

    result = copy.deepcopy(payload)
    target_dialect = "https://json-schema.org/draft/2020-12/schema"
    ref_prefix = "#/definitions/"
    new_ref_prefix = "#/$defs/"

    def visit(schema, root=False):
        if not isinstance(schema, dict):
            return schema

        if root:
            schema["$schema"] = target_dialect

        if "id" in schema:
            schema["$id"] = schema.pop("id")

        if "definitions" in schema:
            schema["$defs"] = schema.pop("definitions")
            if isinstance(schema["$defs"], dict):
                for child in schema["$defs"].values():
                    visit(child)

        if "$ref" in schema and isinstance(schema["$ref"], str) and schema["$ref"].startswith(ref_prefix):
            schema["$ref"] = new_ref_prefix + schema["$ref"][len(ref_prefix):]

        for exclusive, bound in (("exclusiveMinimum", "minimum"), ("exclusiveMaximum", "maximum")):
            if exclusive in schema and isinstance(schema[exclusive], bool):
                if schema[exclusive] is True and bound in schema:
                    schema[exclusive] = schema.pop(bound)
                else:
                    schema.pop(exclusive)

        items = schema.get("items")
        if isinstance(items, list):
            schema["prefixItems"] = items
            schema["items"] = schema.pop("additionalItems") if "additionalItems" in schema else True
            for child in items:
                visit(child)
        else:
            schema.pop("additionalItems", None)
            if isinstance(items, dict):
                visit(items)

        dependencies = schema.pop("dependencies", None)
        if isinstance(dependencies, dict):
            dependent_required = {}
            dependent_schemas = {}
            for key, value in dependencies.items():
                if isinstance(value, list) and all(isinstance(item, str) for item in value):
                    dependent_required[key] = value
                else:
                    dependent_schemas[key] = value
                    visit(value)
            if dependent_required:
                schema["dependentRequired"] = dependent_required
            if dependent_schemas:
                schema["dependentSchemas"] = dependent_schemas

        for keyword in ("properties", "patternProperties"):
            value = schema.get(keyword)
            if isinstance(value, dict):
                for child in value.values():
                    visit(child)

        for keyword in ("additionalProperties", "not"):
            value = schema.get(keyword)
            if isinstance(value, dict):
                visit(value)

        for keyword in ("allOf", "anyOf", "oneOf"):
            value = schema.get(keyword)
            if isinstance(value, list):
                for child in value:
                    visit(child)

        return schema

    return visit(result, root=True)
