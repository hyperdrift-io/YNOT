def transform(payload):
    import copy

    result = copy.deepcopy(payload)
    if not isinstance(result, dict):
        return result

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

        for exclusive, inclusive in (
            ("exclusiveMinimum", "minimum"),
            ("exclusiveMaximum", "maximum"),
        ):
            if exclusive not in schema:
                continue
            value = schema[exclusive]
            if value is True:
                if inclusive in schema:
                    schema[exclusive] = schema.pop(inclusive)
                else:
                    del schema[exclusive]
            elif value is False:
                del schema[exclusive]

        if isinstance(schema.get("items"), list):
            schema["prefixItems"] = schema.pop("items")
            if "additionalItems" in schema:
                schema["items"] = schema.pop("additionalItems")
        else:
            schema.pop("additionalItems", None)

        dependencies = schema.pop("dependencies", None)
        if isinstance(dependencies, dict):
            dependent_required = {}
            dependent_schemas = {}
            for key, value in dependencies.items():
                if isinstance(value, list) and all(isinstance(item, str) for item in value):
                    dependent_required[key] = value
                else:
                    dependent_schemas[key] = value
                    migrate(value)
            if dependent_required:
                schema["dependentRequired"] = dependent_required
            if dependent_schemas:
                schema["dependentSchemas"] = dependent_schemas

        for keyword in ("properties", "patternProperties", "$defs"):
            children = schema.get(keyword)
            if isinstance(children, dict):
                for child in children.values():
                    migrate(child)

        for keyword in ("items", "prefixItems", "additionalItems", "not",
                        "additionalProperties"):
            child = schema.get(keyword)
            if isinstance(child, dict):
                migrate(child)
            elif keyword in ("prefixItems",) and isinstance(child, list):
                for item in child:
                    migrate(item)

        for keyword in ("allOf", "anyOf", "oneOf"):
            children = schema.get(keyword)
            if isinstance(children, list):
                for child in children:
                    migrate(child)

    migrate(result)
    return result