from copy import deepcopy


def transform(payload):
    def migrate(schema):
        if not isinstance(schema, dict):
            return deepcopy(schema)

        result = deepcopy(schema)

        for keyword in ("properties", "patternProperties", "definitions"):
            value = schema.get(keyword)
            if isinstance(value, dict):
                result[keyword] = {
                    name: migrate(child) for name, child in value.items()
                }

        for keyword in ("additionalItems", "additionalProperties", "not"):
            if isinstance(schema.get(keyword), dict):
                result[keyword] = migrate(schema[keyword])

        for keyword in ("allOf", "anyOf", "oneOf"):
            if isinstance(schema.get(keyword), list):
                result[keyword] = [migrate(child) for child in schema[keyword]]

        if "id" in result:
            result["$id"] = result.pop("id")

        if "definitions" in result:
            result["$defs"] = result.pop("definitions")

        ref = result.get("$ref")
        if isinstance(ref, str) and ref.startswith("#/definitions/"):
            result["$ref"] = "#/$defs/" + ref[len("#/definitions/"):]

        for exclusive, inclusive in (
            ("exclusiveMinimum", "minimum"),
            ("exclusiveMaximum", "maximum"),
        ):
            value = result.get(exclusive)
            if value is True:
                if inclusive in result:
                    result[exclusive] = result.pop(inclusive)
                else:
                    result.pop(exclusive)
            elif value is False:
                result.pop(exclusive)

        items = schema.get("items")
        if isinstance(items, list):
            result.pop("items")
            result["prefixItems"] = [migrate(child) for child in items]
            if "additionalItems" in result:
                result["items"] = result.pop("additionalItems")
        else:
            if isinstance(items, dict):
                result["items"] = migrate(items)
            result.pop("additionalItems", None)

        if "dependencies" in schema:
            required = {}
            dependent_schemas = {}
            for name, dependency in schema["dependencies"].items():
                if isinstance(dependency, list):
                    required[name] = deepcopy(dependency)
                else:
                    dependent_schemas[name] = migrate(dependency)
            result.pop("dependencies")
            if required:
                existing = result.get("dependentRequired", {})
                result["dependentRequired"] = {**existing, **required}
            if dependent_schemas:
                existing = result.get("dependentSchemas", {})
                result["dependentSchemas"] = {**existing, **dependent_schemas}

        return result

    result = migrate(payload)
    if isinstance(result, dict):
        result["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    return result