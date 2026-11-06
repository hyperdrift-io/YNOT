def transform(payload):
    import copy

    document = copy.deepcopy(payload)
    draft_uri = "https://json-schema.org/draft/2020-12/schema"

    def migrate(schema, root=False):
        if not isinstance(schema, dict):
            return schema

        if root:
            schema["$schema"] = draft_uri

        if "id" in schema:
            schema["$id"] = schema.pop("id")

        if "definitions" in schema:
            schema["$defs"] = schema.pop("definitions")

        ref = schema.get("$ref")
        if isinstance(ref, str) and ref.startswith("#/definitions/"):
            schema["$ref"] = "#/$defs/" + ref[len("#/definitions/"):]

        for old, bound in (("exclusiveMinimum", "minimum"),
                           ("exclusiveMaximum", "maximum")):
            if old in schema:
                value = schema.pop(old)
                if value is True and bound in schema:
                    schema[old] = schema.pop(bound)

        if isinstance(schema.get("items"), list):
            schema["prefixItems"] = schema.pop("items")
            if "additionalItems" in schema:
                schema["items"] = schema.pop("additionalItems")
        else:
            schema.pop("additionalItems", None)

        dependencies = schema.pop("dependencies", None)
        if isinstance(dependencies, dict):
            required = {}
            dependent_schemas = {}
            for name, value in dependencies.items():
                if isinstance(value, list) and all(isinstance(item, str) for item in value):
                    required[name] = value
                elif isinstance(value, (dict, bool)):
                    dependent_schemas[name] = value
                else:
                    dependent_schemas[name] = value
            if required:
                schema["dependentRequired"] = required
            if dependent_schemas:
                schema["dependentSchemas"] = dependent_schemas

        for keyword in ("properties", "patternProperties", "$defs"):
            members = schema.get(keyword)
            if isinstance(members, dict):
                for child in members.values():
                    migrate(child)

        for keyword in ("items", "prefixItems", "additionalItems",
                        "additionalProperties", "not"):
            child = schema.get(keyword)
            if isinstance(child, (dict, bool)):
                migrate(child)
            elif keyword == "prefixItems" and isinstance(child, list):
                for item in child:
                    migrate(item)

        for keyword in ("allOf", "anyOf", "oneOf"):
            members = schema.get(keyword)
            if isinstance(members, list):
                for child in members:
                    migrate(child)

        return schema

    return migrate(document, root=True)