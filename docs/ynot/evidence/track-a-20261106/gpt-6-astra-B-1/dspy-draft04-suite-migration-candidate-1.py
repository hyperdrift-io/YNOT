from copy import deepcopy

def transform(payload):
    def migrate(schema):
        if not isinstance(schema, dict):
            return deepcopy(schema)

        result = deepcopy(schema)

        for keyword in ("properties", "patternProperties", "definitions"):
            if isinstance(schema.get(keyword), dict):
                result[keyword] = {
                    key: migrate(value)
                    for key, value in schema[keyword].items()
                }

        for keyword in ("additionalItems", "additionalProperties", "not"):
            if isinstance(schema.get(keyword), dict):
                result[keyword] = migrate(schema[keyword])

        for keyword in ("allOf", "anyOf", "oneOf"):
            if isinstance(schema.get(keyword), list):
                result[keyword] = [migrate(value) for value in schema[keyword]]

        if "id" in result:
            result["$id"] = result.pop("id")
        if "definitions" in result:
            result["$defs"] = result.pop("definitions")

        ref = result.get("$ref")
        if isinstance(ref, str) and ref.startswith("#/definitions/"):
            result["$ref"] = "#/$defs/" + ref[len("#/definitions/"):]

        for bound, exclusive in (
            ("minimum", "exclusiveMinimum"),
            ("maximum", "exclusiveMaximum"),
        ):
            value = result.get(exclusive)
            if value is True:
                if bound in result:
                    result[exclusive] = result.pop(bound)
                else:
                    result.pop(exclusive, None)
            elif value is False:
                result.pop(exclusive, None)

        items = schema.get("items")
        if isinstance(items, list):
            result.pop("items", None)
            result["prefixItems"] = [migrate(value) for value in items]
            if "additionalItems" in result:
                result["items"] = result.pop("additionalItems")
        else:
            if isinstance(items, dict):
                result["items"] = migrate(items)
            result.pop("additionalItems", None)

        if isinstance(schema.get("dependencies"), dict):
            required = {}
            dependent = {}
            for key, value in schema["dependencies"].items():
                if isinstance(value, list):
                    required[key] = deepcopy(value)
                else:
                    dependent[key] = migrate(value)
            result.pop("dependencies", None)
            if required:
                existing = result.get("dependentRequired", {})
                result["dependentRequired"] = {**existing, **required}
            if dependent:
                existing = result.get("dependentSchemas", {})
                result["dependentSchemas"] = {**existing, **dependent}

        return result

    result = migrate(payload)
    if isinstance(result, dict):
        result["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    return result