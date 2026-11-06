import copy

DRAFT_2020_12 = "https://json-schema.org/draft/2020-12/schema"


def transform(payload):
    result = copy.deepcopy(payload)
    result["$schema"] = DRAFT_2020_12

    def visit(schema):
        if not isinstance(schema, dict):
            return

        if "id" in schema:
            schema["$id"] = schema.pop("id")

        if "definitions" in schema:
            schema["$defs"] = schema.pop("definitions")
            defs = schema["$defs"]
            if isinstance(defs, dict):
                for child in defs.values():
                    visit(child)

        for key in ("properties", "patternProperties"):
            children = schema.get(key)
            if isinstance(children, dict):
                for child in children.values():
                    visit(child)

        for key in ("exclusiveMinimum", "exclusiveMaximum"):
            bound = "minimum" if key == "exclusiveMinimum" else "maximum"
            value = schema.get(key)
            if value is True:
                if bound in schema:
                    schema[key] = schema.pop(bound)
                else:
                    schema.pop(key, None)
            elif value is False:
                schema.pop(key, None)

        items = schema.get("items")
        if isinstance(items, list):
            schema["prefixItems"] = items
            for child in items:
                visit(child)
            if "additionalItems" in schema:
                schema["items"] = schema.pop("additionalItems")
            else:
                schema.pop("items", None)
        else:
            if "items" in schema:
                visit(items)
            schema.pop("additionalItems", None)

        for key in ("additionalProperties", "not"):
            child = schema.get(key)
            if isinstance(child, dict):
                visit(child)

        for key in ("allOf", "anyOf", "oneOf"):
            children = schema.get(key)
            if isinstance(children, list):
                for child in children:
                    visit(child)

        dependencies = schema.pop("dependencies", None)
        if isinstance(dependencies, dict):
            required = {}
            dependent_schemas = {}
            for name, value in dependencies.items():
                if isinstance(value, list) and all(isinstance(item, str) for item in value):
                    required[name] = value
                else:
                    dependent_schemas[name] = value
                    visit(value)
            if required:
                schema["dependentRequired"] = required
            if dependent_schemas:
                schema["dependentSchemas"] = dependent_schemas

        for key, value in list(schema.items()):
            if key == "$ref" and isinstance(value, str) and value.startswith("#/definitions/"):
                schema[key] = "#/$defs/" + value[len("#/definitions/"):]

    visit(result)
    return result