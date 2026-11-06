def transform(payload):
    schema_uri = "https://json-schema.org/draft/2020-12/schema"

    def migrate(schema, root=False):
        if not isinstance(schema, dict):
            return schema

        result = dict(schema)

        if root:
            result["$schema"] = schema_uri

        if "id" in result:
            result["$id"] = result.pop("id")

        if "$ref" in result and isinstance(result["$ref"], str):
            ref = result["$ref"]
            if ref.startswith("#/definitions/"):
                result["$ref"] = "#/$defs/" + ref[len("#/definitions/"):]

        if "definitions" in result:
            result["$defs"] = result.pop("definitions")

        for keyword in ("exclusiveMinimum", "exclusiveMaximum"):
            bound = "minimum" if keyword == "exclusiveMinimum" else "maximum"
            if result.get(keyword) is True:
                if bound in result:
                    result[keyword] = result.pop(bound)
                else:
                    result.pop(keyword, None)
            elif result.get(keyword) is False:
                result.pop(keyword, None)

        items = result.get("items")
        if isinstance(items, list):
            result["prefixItems"] = [migrate(item) for item in items]
            result.pop("items", None)
            if "additionalItems" in result:
                result["items"] = migrate(result.pop("additionalItems"))
        else:
            if isinstance(items, dict):
                result["items"] = migrate(items)
            if isinstance(result.get("additionalItems"), dict):
                result.pop("additionalItems", None)
            else:
                result.pop("additionalItems", None)

        for keyword in ("properties", "patternProperties", "$defs"):
            value = result.get(keyword)
            if isinstance(value, dict):
                result[keyword] = {key: migrate(child) for key, child in value.items()}

        for keyword in ("additionalProperties", "not"):
            if isinstance(result.get(keyword), dict):
                result[keyword] = migrate(result[keyword])

        for keyword in ("allOf", "anyOf", "oneOf"):
            value = result.get(keyword)
            if isinstance(value, list):
                result[keyword] = [migrate(child) for child in value]

        if "dependencies" in result:
            dependent_required = {}
            dependent_schemas = {}
            dependencies = result.pop("dependencies")
            if isinstance(dependencies, dict):
                for key, value in dependencies.items():
                    if isinstance(value, list) and all(isinstance(item, str) for item in value):
                        dependent_required[key] = value
                    elif isinstance(value, dict):
                        dependent_schemas[key] = migrate(value)
            if dependent_required:
                result["dependentRequired"] = dependent_required
            if dependent_schemas:
                result["dependentSchemas"] = dependent_schemas

        return result

    return migrate(payload, root=True)