def transform(payload):
    import copy

    result = copy.deepcopy(payload)
    schema_uri = "https://json-schema.org/draft/2020-12/schema"

    def visit(schema, root=False):
        if not isinstance(schema, dict):
            return

        if root:
            schema["$schema"] = schema_uri
        if "id" in schema:
            schema["$id"] = schema.pop("id")
        if "definitions" in schema:
            schema["$defs"] = schema.pop("definitions")

        ref = schema.get("$ref")
        if isinstance(ref, str) and ref.startswith("#/definitions/"):
            schema["$ref"] = "#/$defs/" + ref[len("#/definitions/"):]

        for old, bound in (("exclusiveMinimum", "minimum"), ("exclusiveMaximum", "maximum")):
            if old in schema:
                if schema[old] is True and bound in schema:
                    schema[old] = schema.pop(bound)
                else:
                    schema.pop(old)

        items = schema.get("items")
        if isinstance(items, list):
            schema["prefixItems"] = schema.pop("items")
            if "additionalItems" in schema:
                schema["items"] = schema.pop("additionalItems")
            else:
                schema.pop("additionalItems", None)
        else:
            schema.pop("additionalItems", None)

        dependencies = schema.pop("dependencies", None)
        if isinstance(dependencies, dict):
            required, dependent_schemas = {}, {}
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
            children = schema.get(keyword)
            if isinstance(children, dict):
                for child in children.values():
                    visit(child)

        for keyword in ("items", "prefixItems", "additionalItems", "not", "additionalProperties"):
            child = schema.get(keyword)
            if isinstance(child, list):
                for member in child:
                    visit(member)
            elif isinstance(child, dict):
                visit(child)

        for keyword in ("allOf", "anyOf", "oneOf"):
            children = schema.get(keyword)
            if isinstance(children, list):
                for child in children:
                    visit(child)

        dependent_schemas = schema.get("dependentSchemas")
        if isinstance(dependent_schemas, dict):
            for child in dependent_schemas.values():
                visit(child)

    visit(result, root=True)
    return result
