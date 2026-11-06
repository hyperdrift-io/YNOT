def transform(payload):
    import copy

    draft = "https://json-schema.org/draft/2020-12/schema"

    def visit(schema, root=False):
        if not isinstance(schema, dict):
            return schema

        if root:
            schema["$schema"] = draft

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
                if schema[exclusive] is True and bound in schema:
                    schema[exclusive] = schema.pop(bound)
                else:
                    schema.pop(exclusive)

        items = schema.get("items")
        if isinstance(items, list):
            schema["prefixItems"] = [visit(item) for item in items]
            schema.pop("items")
            if "additionalItems" in schema:
                schema["items"] = visit(schema.pop("additionalItems"))
        else:
            if isinstance(items, dict):
                visit(items)
            schema.pop("additionalItems", None)

        for key in ("properties", "patternProperties", "$defs"):
            mapping = schema.get(key)
            if isinstance(mapping, dict):
                for child in mapping.values():
                    visit(child)

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
            dependent_required = {}
            dependent_schemas = {}
            for key, value in dependencies.items():
                if isinstance(value, list) and all(
                    isinstance(item, str) for item in value
                ):
                    dependent_required[key] = value
                elif isinstance(value, (dict, bool)):
                    dependent_schemas[key] = visit(value)

            if dependent_required:
                schema["dependentRequired"] = dependent_required
            if dependent_schemas:
                schema["dependentSchemas"] = dependent_schemas

        return schema

    return visit(copy.deepcopy(payload), root=True)