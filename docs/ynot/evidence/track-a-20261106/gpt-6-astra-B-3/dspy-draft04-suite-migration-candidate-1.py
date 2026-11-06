from copy import deepcopy


def transform(payload):
    def migrate(schema):
        if not isinstance(schema, dict):
            return deepcopy(schema)

        result = deepcopy(schema)

        for keyword in ("properties", "patternProperties", "definitions"):
            values = schema.get(keyword)
            if isinstance(values, dict):
                result[keyword] = {
                    name: migrate(value) for name, value in values.items()
                }

        for keyword in ("additionalProperties", "not"):
            if isinstance(schema.get(keyword), dict):
                result[keyword] = migrate(schema[keyword])

        for keyword in ("allOf", "anyOf", "oneOf"):
            if isinstance(schema.get(keyword), list):
                result[keyword] = [migrate(value) for value in schema[keyword]]

        if "id" in schema:
            result["$id"] = result.pop("id")

        if "definitions" in result:
            result["$defs"] = result.pop("definitions")

        reference = schema.get("$ref")
        if isinstance(reference, str) and reference.startswith("#/definitions/"):
            result["$ref"] = "#/$defs/" + reference[len("#/definitions/"):]

        for exclusive, inclusive in (
            ("exclusiveMinimum", "minimum"),
            ("exclusiveMaximum", "maximum"),
        ):
            value = schema.get(exclusive)
            if value is True:
                if inclusive in schema:
                    result[exclusive] = result.pop(inclusive)
                else:
                    result.pop(exclusive, None)
            elif value is False:
                result.pop(exclusive, None)

        items = schema.get("items")
        if isinstance(items, list):
            result["prefixItems"] = [migrate(value) for value in items]
            result.pop("items", None)
            if "additionalItems" in schema:
                result["items"] = migrate(schema["additionalItems"])
        elif isinstance(items, dict):
            result["items"] = migrate(items)
        result.pop("additionalItems", None)

        if isinstance(schema.get("dependencies"), dict):
            required = {}
            dependent = {}
            for name, value in schema["dependencies"].items():
                if isinstance(value, list):
                    required[name] = deepcopy(value)
                else:
                    dependent[name] = migrate(value)
            result.pop("dependencies", None)
            if required:
                result["dependentRequired"] = required
            if dependent:
                result["dependentSchemas"] = dependent

        return result

    result = migrate(payload)
    result["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    return result