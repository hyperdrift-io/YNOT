from copy import deepcopy


def transform(payload):
    components = payload.get("components", {}).get("schemas", {})
    prefix = "#/components/schemas/"

    def visit_children(schema, operation):
        properties = schema.get("properties")
        if isinstance(properties, dict):
            schema["properties"] = {
                name: operation(value)
                for name, value in properties.items()
            }
        for key in ("items", "additionalProperties", "not"):
            if isinstance(schema.get(key), dict):
                schema[key] = operation(schema[key])
        for key in ("allOf", "anyOf", "oneOf"):
            if isinstance(schema.get(key), list):
                schema[key] = [operation(value) for value in schema[key]]
        return schema

    def resolve(value):
        if not isinstance(value, dict):
            return deepcopy(value)
        ref = value.get("$ref")
        if isinstance(ref, str) and ref.startswith(prefix):
            return resolve(components[ref[len(prefix):]])
        return visit_children(deepcopy(value), resolve)

    def nullable(value):
        if not isinstance(value, dict):
            return value
        if value.get("nullable") is True and isinstance(value.get("type"), str):
            kind = value["type"]
            value["type"] = [kind, "null"] if kind != "null" else ["null"]
        value.pop("nullable", None)
        return visit_children(value, nullable)

    def permit_null(schema):
        if not isinstance(schema, dict):
            return
        kind = schema.get("type")
        if isinstance(kind, str) and kind != "null":
            schema["type"] = [kind, "null"]
        elif isinstance(kind, list) and "null" not in kind:
            schema["type"] = kind + ["null"]
        enum = schema.get("enum")
        if isinstance(enum, list) and None not in enum:
            schema["enum"] = enum + [None]

    def strict(value):
        if not isinstance(value, dict):
            return value
        original_required = value.get("required", [])
        value.pop("default", None)
        visit_children(value, strict)
        properties = value.get("properties")
        if isinstance(properties, dict):
            for name, schema in properties.items():
                if name not in original_required:
                    permit_null(schema)
            value["additionalProperties"] = False
            value["required"] = sorted(properties)
        return value

    return {
        name: strict(nullable(resolve(schema)))
        for name, schema in components.items()
    }