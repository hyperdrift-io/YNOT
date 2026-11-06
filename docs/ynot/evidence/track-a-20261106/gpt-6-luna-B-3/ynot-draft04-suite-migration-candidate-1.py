from copy import deepcopy


def transform(payload):
    result = deepcopy(payload)

    def visit(schema, is_root=False):
        if not isinstance(schema, dict):
            return schema

        if is_root:
            schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"

        if "id" in schema:
            schema["$id"] = schema.pop("id")

        if "definitions" in schema:
            definitions = schema.pop("definitions")
            if "$defs" in schema and isinstance(definitions, dict) and isinstance(schema["$defs"], dict):
                schema["$defs"] = {**definitions, **schema["$defs"]}
            elif "$defs" not in schema:
                schema["$defs"] = definitions

        for key, value in list(schema.items()):
            if key == "$ref" and isinstance(value, str) and value.startswith("#/definitions/"):
                schema[key] = "#/$defs/" + value[len("#/definitions/"):]

        for exclusive, bound in (("exclusiveMinimum", "minimum"), ("exclusiveMaximum", "maximum")):
            if exclusive in schema:
                if schema[exclusive] is True and bound in schema:
                    schema[exclusive] = schema.pop(bound)
                else:
                    schema.pop(exclusive)

        items = schema.get("items")
        if isinstance(items, list):
            schema["prefixItems"] = items
            schema.pop("items")
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
            if required:
                existing = schema.get("dependentRequired")
                if isinstance(existing, dict):
                    schema["dependentRequired"] = {**required, **existing}
                else:
                    schema["dependentRequired"] = required
            if dependent_schemas:
                existing = schema.get("dependentSchemas")
                if isinstance(existing, dict):
                    schema["dependentSchemas"] = {**dependent_schemas, **existing}
                else:
                    schema["dependentSchemas"] = dependent_schemas

        def visit_map(key):
            value = schema.get(key)
            if isinstance(value, dict):
                for child in value.values():
                    visit(child)

        for key in ("properties", "patternProperties", "$defs"):
            visit_map(key)

        items = schema.get("items")
        if isinstance(items, dict):
            visit(items)
        elif isinstance(items, list):
            for child in items:
                visit(child)

        for key in ("additionalItems", "not"):
            child = schema.get(key)
            if isinstance(child, dict):
                visit(child)

        child = schema.get("additionalProperties")
        if isinstance(child, dict):
            visit(child)

        for key in ("dependentSchemas",):
            visit_map(key)

        for key in ("allOf", "anyOf", "oneOf"):
            children = schema.get(key)
            if isinstance(children, list):
                for child in children:
                    visit(child)

        return schema

    return visit(result, is_root=True)