from copy import deepcopy

def transform(payload):
    components = payload["components"]["schemas"]

    def resolve(schema):
        if isinstance(schema, dict):
            ref = schema.get("$ref")
            if isinstance(ref, str) and ref.startswith("#/components/schemas/"):
                name = ref[len("#/components/schemas/"):]
                return resolve(deepcopy(components[name]))
            result = {}
            for key, value in schema.items():
                if key in ("properties",) and isinstance(value, dict):
                    result[key] = {name: resolve(child) for name, child in value.items()}
                elif key in ("items", "additionalProperties", "not") and isinstance(value, dict):
                    result[key] = resolve(value)
                elif key in ("allOf", "anyOf", "oneOf") and isinstance(value, list):
                    result[key] = [resolve(child) for child in value]
                else:
                    result[key] = deepcopy(value)
            return result
        return deepcopy(schema)

    resolved = {name: resolve(schema) for name, schema in components.items()}

    def prepare(schema):
        if not isinstance(schema, dict):
            return
        nullable = schema.pop("nullable", None)
        if nullable is True and isinstance(schema.get("type"), str):
            schema["type"] = [schema["type"], "null"]
        schema.pop("default", None)
        props = schema.get("properties")
        if isinstance(props, dict):
            original_required = schema.get("required", [])
            original_required = original_required if isinstance(original_required, list) else []
            for name, child in props.items():
                prepare(child)
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
        if isinstance(schema.get("items"), dict):
            prepare(schema["items"])
        if isinstance(schema.get("additionalProperties"), dict):
            prepare(schema["additionalProperties"])
        if isinstance(schema.get("not"), dict):
            prepare(schema["not"])
        for key in ("allOf", "anyOf", "oneOf"):
            value = schema.get(key)
            if isinstance(value, list):
                for child in value:
                    prepare(child)

    for schema in resolved.values():
        prepare(schema)
    return resolved