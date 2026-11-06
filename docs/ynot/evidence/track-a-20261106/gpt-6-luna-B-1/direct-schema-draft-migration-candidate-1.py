def transform(payload):
    import copy

    result = copy.deepcopy(payload)
    target_dialect = "https://json-schema.org/draft/2020-12/schema"

    def visit(schema, root=False):
        if not isinstance(schema, dict):
            return

        if root:
            schema["$schema"] = target_dialect
        if "id" in schema:
            schema["$id"] = schema.pop("id")
        if "definitions" in schema:
            schema["$defs"] = schema.pop("definitions")
        if isinstance(schema.get("$ref"), str) and schema["$ref"].startswith("#/definitions/"):
            schema["$ref"] = "#/$defs/" + schema["$ref"][len("#/definitions/"):]

        for exclusive, inclusive in (("exclusiveMinimum", "minimum"), ("exclusiveMaximum", "maximum")):
            if schema.get(exclusive) is True:
                if inclusive in schema:
                    schema[exclusive] = schema.pop(inclusive)
                else:
                    schema.pop(exclusive, None)
            elif schema.get(exclusive) is False:
                schema.pop(exclusive, None)

        if isinstance(schema.get("items"), list):
            schema["prefixItems"] = schema.pop("items")
            if "additionalItems" in schema:
                schema["items"] = schema.pop("additionalItems")
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

        for keyword in ("properties", "patternProperties", "definitions"):
            members = schema.get(keyword)
            if isinstance(members, dict):
                for child in members.values():
                    visit(child)
        defs = schema.get("$defs")
        if isinstance(defs, dict):
            for child in defs.values():
                visit(child)

        deps = schema.get("dependentSchemas")
        if isinstance(deps, dict):
            for child in deps.values():
                visit(child)

        items = schema.get("items")
        if isinstance(items, dict):
            visit(items)
        elif isinstance(items, list):
            for child in items:
                visit(child)
        prefix = schema.get("prefixItems")
        if isinstance(prefix, list):
            for child in prefix:
                visit(child)

        for keyword in ("additionalItems", "additionalProperties", "not"):
            child = schema.get(keyword)
            if isinstance(child, dict):
                visit(child)
        for keyword in ("allOf", "anyOf", "oneOf"):
            members = schema.get(keyword)
            if isinstance(members, list):
                for child in members:
                    visit(child)

    visit(result, True)
    return result