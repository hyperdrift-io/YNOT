def transform(payload):
    from copy import deepcopy

    schemas = payload.get("components", {}).get("schemas", {})

    def resolve(value):
        if isinstance(value, dict):
            ref = value.get("$ref")
            if isinstance(ref, str) and ref.startswith("#/components/schemas/"):
                name = ref[len("#/components/schemas/"):]
                value = deepcopy(schemas[name])
            return {key: resolve(child) for key, child in value.items()}
        if isinstance(value, list):
            return [resolve(child) for child in value]
        return value

    def walk(schema):
        if isinstance(schema, dict):
            for key in list(schema):
                if key == "nullable":
                    nullable = schema.pop(key)
                    if nullable is True and isinstance(schema.get("type"), str):
                        schema["type"] = [schema["type"], "null"]
                elif key == "default":
                    schema.pop(key)
                elif key == "properties" and isinstance(schema[key], dict):
                    original_required = schema.get("required", [])
                    originally_required = set(original_required) if isinstance(original_required, list) else set()
                    properties = schema[key]
                    for name, child in properties.items():
                        if name not in originally_required and isinstance(child, dict):
                            typ = child.get("type")
                            if isinstance(typ, str) and typ != "null":
                                child["type"] = [typ, "null"]
                            elif isinstance(typ, list) and "null" not in typ:
                                child["type"] = typ + ["null"]
                            enum = child.get("enum")
                            if isinstance(enum, list) and None not in enum:
                                child["enum"] = enum + [None]
                    schema["additionalProperties"] = False
                    schema["required"] = sorted(properties)
                    for child in properties.values():
                        walk(child)
                elif key in ("items", "not") and isinstance(schema[key], (dict, list)):
                    walk(schema[key])
                elif key == "additionalProperties" and isinstance(schema[key], dict):
                    walk(schema[key])
                elif key in ("allOf", "anyOf", "oneOf") and isinstance(schema[key], list):
                    for child in schema[key]:
                        walk(child)

    result = {}
    for name, component in schemas.items():
        prepared = resolve(deepcopy(component))
        walk(prepared)
        result[name] = prepared
    return result