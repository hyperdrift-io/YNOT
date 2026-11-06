from copy import deepcopy


def transform(payload):
    def migrate(schema):
        if not isinstance(schema, dict):
            return deepcopy(schema)

        result = deepcopy(schema)

        if "id" in schema:
            result["$id"] = result.pop("id")

        ref = schema.get("$ref")
        if isinstance(ref, str) and ref.startswith("#/definitions/"):
            result["$ref"] = "#/$defs/" + ref[len("#/definitions/"):]

        for keyword in ("properties", "patternProperties", "definitions"):
            if keyword in schema:
                migrated = {
                    name: migrate(value)
                    for name, value in schema[keyword].items()
                }
                if keyword == "definitions":
                    result.pop("definitions")
                    result["$defs"] = migrated
                else:
                    result[keyword] = migrated

        for exclusive, bound in (
            ("exclusiveMinimum", "minimum"),
            ("exclusiveMaximum", "maximum"),
        ):
            value = schema.get(exclusive)
            if value is True:
                if bound in schema:
                    result[exclusive] = deepcopy(schema[bound])
                    result.pop(bound, None)
                else:
                    result.pop(exclusive, None)
            elif value is False:
                result.pop(exclusive, None)

        items = schema.get("items")
        if isinstance(items, list):
            result.pop("items")
            result["prefixItems"] = [migrate(item) for item in items]
            if "additionalItems" in schema:
                result["items"] = migrate(schema["additionalItems"])
        elif "items" in schema:
            result["items"] = migrate(items)
        result.pop("additionalItems", None)

        if isinstance(schema.get("additionalProperties"), dict):
            result["additionalProperties"] = migrate(
                schema["additionalProperties"]
            )

        if "not" in schema:
            result["not"] = migrate(schema["not"])

        for keyword in ("allOf", "anyOf", "oneOf"):
            if keyword in schema:
                result[keyword] = [migrate(item) for item in schema[keyword]]

        if "dependencies" in schema:
            required = {}
            dependent_schemas = {}
            for name, value in schema["dependencies"].items():
                if isinstance(value, list) and all(
                    isinstance(item, str) for item in value
                ):
                    required[name] = deepcopy(value)
                else:
                    dependent_schemas[name] = migrate(value)
            result.pop("dependencies")
            if required:
                merged = deepcopy(result.get("dependentRequired", {}))
                merged.update(required)
                result["dependentRequired"] = merged
            if dependent_schemas:
                merged = deepcopy(result.get("dependentSchemas", {}))
                merged.update(dependent_schemas)
                result["dependentSchemas"] = merged

        return result

    result = migrate(payload)
    result["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    return result