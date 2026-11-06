from copy import deepcopy


def transform(payload):
    def migrate(schema):
        if not isinstance(schema, dict):
            return deepcopy(schema)

        result = deepcopy(schema)

        for keyword in ("properties", "patternProperties", "definitions"):
            values = result.get(keyword)
            if isinstance(values, dict):
                result[keyword] = {
                    name: migrate(value) for name, value in values.items()
                }

        for keyword in ("additionalItems", "additionalProperties", "not"):
            if isinstance(result.get(keyword), dict):
                result[keyword] = migrate(result[keyword])

        for keyword in ("allOf", "anyOf", "oneOf"):
            if isinstance(result.get(keyword), list):
                result[keyword] = [migrate(value) for value in result[keyword]]

        if "id" in result:
            result["$id"] = result.pop("id")

        if "definitions" in result:
            result["$defs"] = result.pop("definitions")

        reference = result.get("$ref")
        if isinstance(reference, str) and reference.startswith("#/definitions/"):
            result["$ref"] = "#/$defs/" + reference[len("#/definitions/"):]

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

        if isinstance(result.get("items"), list):
            result["prefixItems"] = [
                migrate(value) for value in result.pop("items")
            ]
            if "additionalItems" in result:
                result["items"] = result.pop("additionalItems")
        else:
            if isinstance(result.get("items"), dict):
                result["items"] = migrate(result["items"])
            result.pop("additionalItems", None)

        if "dependencies" in result:
            dependencies = result.pop("dependencies")
            required = {}
            schemas = {}
            for name, value in dependencies.items():
                if isinstance(value, list) and all(
                    isinstance(item, str) for item in value
                ):
                    required[name] = value
                else:
                    schemas[name] = migrate(value)
            if required:
                result.setdefault("dependentRequired", {}).update(required)
            if schemas:
                result.setdefault("dependentSchemas", {}).update(schemas)

        return result

    result = migrate(payload)
    if isinstance(result, dict):
        result["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    return result