def transform(payload):
    import copy

    result = copy.deepcopy(payload)
    target_dialect = "https://json-schema.org/draft/2020-12/schema"

    def visit(schema, root=False):
        if not isinstance(schema, dict):
            return schema

        if root:
            schema["$schema"] = target_dialect
        if "id" in schema:
            schema["$id"] = schema.pop("id")
        if "definitions" in schema:
            schema["$defs"] = schema.pop("definitions")

        ref = schema.get("$ref")
        if isinstance(ref, str) and ref.startswith("#/definitions/"):
            schema["$ref"] = "#/$defs/" + ref[len("#/definitions/"):]

        for exclusive, inclusive in (("exclusiveMinimum", "minimum"), ("exclusiveMaximum", "maximum")):
            if isinstance(schema.get(exclusive), bool):
                if schema[exclusive] is True and inclusive in schema:
                    schema[exclusive] = schema.pop(inclusive)
                else:
                    schema.pop(exclusive)

        if isinstance(schema.get("items"), list):
            schema["prefixItems"] = schema.pop("items")
            if "additionalItems" in schema:
                schema["items"] = schema.pop("additionalItems")
            else:
                schema.pop("items", None)
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

        for keyword in ("properties", "patternProperties", "definitions"):
            children = schema.get(keyword)
            if isinstance(children, dict):
                for child in children.values():
                    visit(child)
        # Draft-04 definitions were renamed above.
        children = schema.get("$defs")
        if isinstance(children, dict):
            for child in children.values():
                visit(child)

        for keyword in ("items", "additionalItems", "additionalProperties", "not"):
            child = schema.get(keyword)
            if isinstance(child, dict):
                visit(child)
            elif keyword == "items" and isinstance(child, list):
                for item in child:
                    visit(item)

        for keyword in ("allOf", "anyOf", "oneOf"):
            children = schema.get(keyword)
            if isinstance(children, list):
                for child in children:
                    visit(child)

        children = schema.get("dependentSchemas")
        if isinstance(children, dict):
            for child in children.values():
                visit(child)
        return schema

    return visit(result, root=True)
