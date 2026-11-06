def transform(payload):
    import copy

    result = copy.deepcopy(payload)
    if not isinstance(result, dict):
        return result

    result["$schema"] = "https://json-schema.org/draft/2020-12/schema"

    def migrate(schema, is_root=False):
        if not isinstance(schema, dict):
            return

        if "id" in schema:
            schema["$id"] = schema.pop("id")

        if "definitions" in schema:
            schema["$defs"] = schema.pop("definitions")

        for key in ("exclusiveMinimum", "exclusiveMaximum"):
            bound = "minimum" if key == "exclusiveMinimum" else "maximum"
            if key in schema:
                value = schema[key]
                if value is True and bound in schema:
                    schema[key] = schema.pop(bound)
                elif value is False or value is True:
                    schema.pop(key)

        if isinstance(schema.get("items"), list):
            schema["prefixItems"] = schema.pop("items")
            if "additionalItems" in schema:
                schema["items"] = schema.pop("additionalItems")
        else:
            schema.pop("additionalItems", None)

        dependencies = schema.pop("dependencies", None)
        if isinstance(dependencies, dict):
            required, dependent_schemas = {}, {}
            for name, value in dependencies.items():
                if isinstance(value, list) and all(isinstance(item, str) for item in value):
                    required[name] = value
                else:
                    dependent_schemas[name] = value
                    migrate(value)
            if required:
                schema["dependentRequired"] = required
            if dependent_schemas:
                schema["dependentSchemas"] = dependent_schemas

        ref = schema.get("$ref")
        if isinstance(ref, str) and ref.startswith("#/definitions/"):
            schema["$ref"] = "#/$defs/" + ref[len("#/definitions/"):]

        for key in ("properties", "patternProperties", "$defs"):
            mapping = schema.get(key)
            if isinstance(mapping, dict):
                for child in mapping.values():
                    migrate(child)

        for key in ("items", "prefixItems", "additionalItems", "not", "additionalProperties"):
            child = schema.get(key)
            if isinstance(child, list):
                for item in child:
                    migrate(item)
            elif isinstance(child, dict):
                migrate(child)

        for key in ("allOf", "anyOf", "oneOf"):
            children = schema.get(key)
            if isinstance(children, list):
                for child in children:
                    migrate(child)

    migrate(result, True)
    return result