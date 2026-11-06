def transform(payload):
    import copy

    result = copy.deepcopy(payload)
    draft_uri = "https://json-schema.org/draft/2020-12/schema"

    def migrate(schema, root=False):
        if not isinstance(schema, dict):
            return

        if root:
            schema["$schema"] = draft_uri

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
            if schema.get(exclusive) is True and bound in schema:
                schema[exclusive] = schema.pop(bound)
            elif exclusive in schema:
                del schema[exclusive]

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
                if isinstance(value, list) and all(
                    isinstance(item, str) for item in value
                ):
                    required[name] = value
                else:
                    dependent_schemas[name] = value
            if required:
                schema["dependentRequired"] = required
            if dependent_schemas:
                schema["dependentSchemas"] = dependent_schemas

        for keyword in ("properties", "patternProperties", "$defs"):
            children = schema.get(keyword)
            if isinstance(children, dict):
                for child in children.values():
                    migrate(child)

        for keyword in ("items", "prefixItems", "additionalItems", "not"):
            child = schema.get(keyword)
            if isinstance(child, dict):
                migrate(child)
            elif isinstance(child, list):
                for member in child:
                    migrate(member)

        child = schema.get("additionalProperties")
        if isinstance(child, dict):
            migrate(child)

        for keyword in ("allOf", "anyOf", "oneOf"):
            children = schema.get(keyword)
            if isinstance(children, list):
                for child in children:
                    migrate(child)

        children = schema.get("dependentSchemas")
        if isinstance(children, dict):
            for child in children.values():
                migrate(child)

    migrate(result, root=True)
    return result