def transform(payload):
    schema_uri = "https://json-schema.org/draft/2020-12/schema"

    def migrate(schema, is_root=False):
        if not isinstance(schema, dict):
            return schema

        result = dict(schema)

        if is_root:
            result["$schema"] = schema_uri

        if "id" in result:
            result["$id"] = result.pop("id")

        ref = result.get("$ref")
        if isinstance(ref, str) and ref.startswith("#/definitions/"):
            result["$ref"] = "#/$defs/" + ref[len("#/definitions/"):]

        if "definitions" in result:
            result["$defs"] = result.pop("definitions")

        for exclusive, inclusive in (
            ("exclusiveMinimum", "minimum"),
            ("exclusiveMaximum", "maximum"),
        ):
            value = result.get(exclusive)
            if value is True:
                if inclusive in result:
                    result[exclusive] = result.pop(inclusive)
                else:
                    result.pop(exclusive, None)
            elif value is False:
                result.pop(exclusive, None)

        items = result.get("items")
        if isinstance(items, list):
            result["prefixItems"] = [migrate(item) for item in items]
            result.pop("items", None)
            if "additionalItems" in result:
                result["items"] = migrate(result.pop("additionalItems"))
        else:
            if isinstance(items, dict):
                result["items"] = migrate(items)
            result.pop("additionalItems", None)

        for keyword in ("properties", "patternProperties", "$defs"):
            value = result.get(keyword)
            if isinstance(value, dict):
                result[keyword] = {
                    name: migrate(child) for name, child in value.items()
                }

        for keyword in ("additionalProperties", "not"):
            if isinstance(result.get(keyword), dict):
                result[keyword] = migrate(result[keyword])

        for keyword in ("allOf", "anyOf", "oneOf"):
            value = result.get(keyword)
            if isinstance(value, list):
                result[keyword] = [migrate(child) for child in value]

        if "dependencies" in result:
            required = {}
            schemas = {}
            dependencies = result.pop("dependencies")
            if isinstance(dependencies, dict):
                for name, value in dependencies.items():
                    if isinstance(value, list) and all(
                        isinstance(item, str) for item in value
                    ):
                        required[name] = value
                    elif isinstance(value, dict):
                        schemas[name] = migrate(value)
            if required:
                result["dependentRequired"] = required
            if schemas:
                result["dependentSchemas"] = schemas

        return result

    return migrate(payload, is_root=True)