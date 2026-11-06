import copy

def transform(payload):
    doc = copy.deepcopy(payload)
    new_dependencies = {}

    def visit(schema, is_root=False):
        if not isinstance(schema, dict):
            return

        if is_root:
            schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"

        if "id" in schema:
            schema["$id"] = schema.pop("id")

        if "definitions" in schema:
            definitions = schema.pop("definitions")
            schema["$defs"] = definitions
            if isinstance(definitions, dict):
                for child in definitions.values():
                    visit(child)

        if "$ref" in schema and isinstance(schema["$ref"], str):
            if schema["$ref"].startswith("#/definitions/"):
                schema["$ref"] = "#/$defs/" + schema["$ref"][len("#/definitions/"):]

        for old, bound in (("exclusiveMinimum", "minimum"), ("exclusiveMaximum", "maximum")):
            if old in schema:
                value = schema[old]
                if value is True and bound in schema:
                    schema[old] = schema.pop(bound)
                else:
                    schema.pop(old)

        if isinstance(schema.get("items"), list):
            schema["prefixItems"] = schema.pop("items")
            if "additionalItems" in schema:
                schema["items"] = schema.pop("additionalItems")
            else:
                schema.pop("additionalItems", None)
            for child in schema["prefixItems"]:
                visit(child)
        else:
            if isinstance(schema.get("items"), dict):
                visit(schema["items"])
            schema.pop("additionalItems", None)

        for key in ("properties", "patternProperties"):
            mapping = schema.get(key)
            if isinstance(mapping, dict):
                for child in mapping.values():
                    visit(child)

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
            required, dependent_schemas = {}, {}
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

    visit(doc, True)
    return doc