def transform(payload):
    import copy

    result = copy.deepcopy(payload)
    if not isinstance(result, dict):
        return result

    def migrate(schema, root=False):
        if not isinstance(schema, dict):
            return schema

        if root:
            schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"

        if "id" in schema:
            schema["$id"] = schema.pop("id")

        definitions = schema.pop("definitions", None)
        if definitions is not None:
            schema["$defs"] = definitions

        ref = schema.get("$ref")
        if isinstance(ref, str) and ref.startswith("#/definitions/"):
            schema["$ref"] = "#/$defs/" + ref[len("#/definitions/"):]

        for bound, inclusive in (
            ("minimum", "exclusiveMinimum"),
            ("maximum", "exclusiveMaximum"),
        ):
            if inclusive in schema and isinstance(schema[inclusive], bool):
                flag = schema[inclusive]
                if flag and bound in schema:
                    schema[inclusive] = schema.pop(bound)
                else:
                    schema.pop(inclusive)

        if isinstance(schema.get("items"), list):
            schema["prefixItems"] = schema.pop("items")
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

        for keyword in ("properties", "patternProperties", "definitions"):
            mapping = schema.get(keyword)
            if isinstance(mapping, dict):
                for value in mapping.values():
                    migrate(value)

        defs = schema.get("$defs")
        if isinstance(defs, dict):
            for value in defs.values():
                migrate(value)

        deps = schema.get("dependentSchemas")
        if isinstance(deps, dict):
            for value in deps.values():
                migrate(value)

        items = schema.get("items")
        if isinstance(items, dict):
            migrate(items)
        prefix = schema.get("prefixItems")
        if isinstance(prefix, list):
            for value in prefix:
                migrate(value)

        for keyword in ("additionalItems", "additionalProperties", "not"):
            value = schema.get(keyword)
            if isinstance(value, dict):
                migrate(value)

        for keyword in ("allOf", "anyOf", "oneOf"):
            subschemas = schema.get(keyword)
            if isinstance(subschemas, list):
                for value in subschemas:
                    migrate(value)

        return schema

    return migrate(result, root=True)