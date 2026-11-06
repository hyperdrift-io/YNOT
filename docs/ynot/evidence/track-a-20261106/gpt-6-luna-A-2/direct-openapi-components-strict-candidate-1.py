from copy import deepcopy


def transform(payload):
    components = payload.get("components", {}).get("schemas", {})

    def resolve(value):
        if isinstance(value, list):
            return [resolve(item) for item in value]
        if not isinstance(value, dict):
            return value
        ref = value.get("$ref")
        if isinstance(ref, str) and ref.startswith("#/components/schemas/"):
            name = ref[len("#/components/schemas/"):]
            return resolve(deepcopy(components[name]))
        return {key: resolve(item) for key, item in value.items()}

    def schema_children(schema):
        children = []
        properties = schema.get("properties")
        if isinstance(properties, dict):
            children.extend(properties.values())
        for key in ("items", "not"):
            child = schema.get(key)
            if isinstance(child, dict):
                children.append(child)
        additional = schema.get("additionalProperties")
        if isinstance(additional, dict):
            children.append(additional)
        for key in ("allOf", "anyOf", "oneOf"):
            value = schema.get(key)
            if isinstance(value, list):
                children.extend(item for item in value if isinstance(item, dict))
        return children

    def prepare(schema):
        if not isinstance(schema, dict):
            return
        nullable = schema.pop("nullable", None)
        if nullable is True and isinstance(schema.get("type"), str):
            schema["type"] = [schema["type"], "null"]
        schema.pop("default", None)
        properties = schema.get("properties")
        if isinstance(properties, dict):
            original_required = schema.get("required", [])
            originally_required = set(original_required) if isinstance(original_required, list) else set()
            schema["additionalProperties"] = False
            schema["required"] = sorted(properties)
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
        for child in schema_children(schema):
            prepare(child)

    result = {}
    for name, component in components.items():
        schema = resolve(deepcopy(component))
        prepare(schema)
        result[name] = schema
    return result