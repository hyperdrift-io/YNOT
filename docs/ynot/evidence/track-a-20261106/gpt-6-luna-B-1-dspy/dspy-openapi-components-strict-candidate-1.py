def transform(payload):
    import copy

    components = payload.get("components", {}).get("schemas", {})
    memo = {}

    def resolve(schema):
        if isinstance(schema, dict) and isinstance(schema.get("$ref"), str):
            ref = schema["$ref"]
            prefix = "#/components/schemas/"
            if ref.startswith(prefix):
                name = ref[len(prefix):]
                if name not in components:
                    raise KeyError(name)
                return resolve(copy.deepcopy(components[name]))
        if isinstance(schema, list):
            return [resolve(item) for item in schema]
        if isinstance(schema, dict):
            return {
                key: resolve(value) if key in {
                    "properties", "items", "additionalProperties", "not",
                    "allOf", "anyOf", "oneOf"
                } else copy.deepcopy(value)
                for key, value in schema.items()
            }
        return copy.deepcopy(schema)

    def prepare(schema):
        if isinstance(schema, list):
            return [prepare(item) for item in schema]
        if not isinstance(schema, dict):
            return schema

        original_required = schema.get("required", [])
        properties = schema.get("properties")
        prepared = {}
        for key, value in schema.items():
            if key == "nullable":
                continue
            if key == "default":
                continue
            if key == "properties" and isinstance(value, dict):
                prepared[key] = {name: prepare(prop) for name, prop in value.items()}
            elif key in {"items", "additionalProperties", "not"} and isinstance(value, (dict, list)):
                prepared[key] = prepare(value)
            elif key in {"allOf", "anyOf", "oneOf"} and isinstance(value, list):
                prepared[key] = [prepare(member) for member in value]
            else:
                prepared[key] = copy.deepcopy(value)

        if schema.get("nullable") is True and isinstance(schema.get("type"), str):
            typ = schema["type"]
            prepared["type"] = [typ, "null"]

        if isinstance(properties, dict):
            names = sorted(properties)
            prepared["additionalProperties"] = False
            prepared["required"] = names
            for name in names:
                if name not in original_required:
                    prop = prepared["properties"][name]
                    if isinstance(prop, dict):
                        typ = prop.get("type")
                        if isinstance(typ, str) and typ != "null":
                            prop["type"] = [typ, "null"]
                        elif isinstance(typ, list) and "null" not in typ:
                            prop["type"] = typ + ["null"]
                        enum = prop.get("enum")
                        if isinstance(enum, list) and None not in enum:
                            prop["enum"] = enum + [None]

        return prepared

    result = {}
    for name, component in components.items():
        result[name] = prepare(resolve(component))
    return result