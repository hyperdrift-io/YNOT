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

        for keyword in ("items", "additionalItems", "additionalProperties", "not"):
            value = schema.get(keyword)
            if isinstance(value, dict):
                result[keyword] = migrate(value)
            elif keyword == "items" and isinstance(value, list):
                result[keyword] = [migrate(child) for child in value]

        for keyword in ("allOf", "anyOf", "oneOf"):
            value = schema.get(keyword)
            if isinstance(value, list):
                result[keyword] = [migrate(child) for child in value]

        if "id" in result:
            result["$id"] = result.pop("id")

        if "definitions" in result:
            result["$defs"] = result.pop("definitions")

        reference = result.get("$ref")
        if isinstance(reference, str) and reference.startswith("#/definitions/"):
            result["$ref"] = "#/$defs/" + reference[len("#/definitions/"):]

        for exclusive, bound in (
            ("exclusiveMinimum", "minimum"),
            ("exclusiveMaximum", "maximum"),
        ):
            if result.get(exclusive) is True:
                if bound in result:
                    result[exclusive] = result.pop(bound)
                else:
                    result.pop(exclusive)
            elif result.get(exclusive) is False:
                result.pop(exclusive)

        if isinstance(schema.get("items"), list):
            result["prefixItems"] = result.pop("items")
            if "additionalItems" in result:
                result["items"] = result.pop("additionalItems")
        else:
            result.pop("additionalItems", None)

        if "dependencies" in schema:
            dependencies = result.pop("dependencies")
            required = {}
            dependent_schemas = {}
            for name, value in dependencies.items():
                if isinstance(value, list) and all(
                    isinstance(item, str) for item in value
                ):
                    required[name] = deepcopy(value)
                else:
                    dependent_schemas[name] = migrate(value)

            if required:
                existing = result.get("dependentRequired", {})
                result["dependentRequired"] = {**existing, **required}
            if dependent_schemas:
                existing = result.get("dependentSchemas", {})
                result["dependentSchemas"] = {**existing, **dependent_schemas}

        return result

    result = migrate(payload)
    result["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    return result