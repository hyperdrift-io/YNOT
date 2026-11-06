from copy import deepcopy

def transform(payload):
    components = payload["components"]["schemas"]

    def resolve(node):
        if isinstance(node, dict):
            ref = node.get("$ref")
            if isinstance(ref, str) and ref.startswith("#/components/schemas/"):
                name = ref[len("#/components/schemas/"):]
                return resolve(deepcopy(components[name]))
            return {key: resolve(value) if is_schema_child(node, key, value) else deepcopy(value)
                    for key, value in node.items()}
        if isinstance(node, list):
            return [resolve(value) for value in node]
        return deepcopy(node)

    def is_schema_child(parent, key, value):
        if key in ("properties",) and isinstance(value, dict):
            return True
        if key in ("items", "not") and isinstance(value, (dict, list)):
            return True
        if key == "additionalProperties" and isinstance(value, dict):
            return True
        if key in ("allOf", "anyOf", "oneOf") and isinstance(value, list):
            return True
        return False

    resolved = {name: resolve(schema) for name, schema in components.items()}

    def walk(schema, original_required=None):
        if isinstance(schema, list):
            return [walk(item) for item in schema]
        if not isinstance(schema, dict):
            return schema
        original_required = original_required or []
        props = schema.get("properties")
        if isinstance(props, dict):
            for name, child in list(props.items()):
                if name not in original_required and isinstance(child, dict):
                    typ = child.get("type")
                    if isinstance(typ, str) and typ != "null":
                        child["type"] = [typ, "null"]
                    elif isinstance(typ, list) and "null" not in typ:
                        child["type"] = typ + ["null"]
                    enum = child.get("enum")
                    if isinstance(enum, list) and None not in enum:
                        child["enum"] = enum + [None]
            schema["additionalProperties"] = False
            schema["required"] = sorted(props)
        schema.pop("default", None)
        nullable = schema.pop("nullable", None)
        typ = schema.get("type")
        if nullable is True and isinstance(typ, str):
            schema["type"] = [typ, "null"]
        old_required = original_required
        for key, value in list(schema.items()):
            if key == "properties" and isinstance(value, dict):
                for child in value.values():
                    walk(child)
            elif key in ("items", "not") and isinstance(value, dict):
                walk(value)
            elif key == "additionalProperties" and isinstance(value, dict):
                walk(value)
            elif key in ("allOf", "anyOf", "oneOf") and isinstance(value, list):
                for child in value:
                    walk(child)
        return schema

    result = {}
    for name, schema in resolved.items():
        result[name] = walk(schema, schema.get("required", []) if isinstance(schema, dict) else [])
    return result