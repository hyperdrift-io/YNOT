def transform(payload):
    import copy

    components = payload.get("components", {}).get("schemas", {})

    def resolve(schema, stack=()):
        if isinstance(schema, list):
            return [resolve(item, stack) for item in schema]
        if not isinstance(schema, dict):
            return copy.deepcopy(schema)

        ref = schema.get("$ref")
        if isinstance(ref, str) and ref.startswith("#/components/schemas/"):
            name = ref[len("#/components/schemas/"):]
            if name not in components or "/" in name:
                raise ValueError("Unresolvable component reference")
            if name in stack:
                raise ValueError("Reference cycle")
            return resolve(components[name], stack + (name,))

        result = {}
        for key, value in schema.items():
            if key == "nullable":
                continue
            if key == "default":
                continue
            if key == "properties" and isinstance(value, dict):
                result[key] = {k: resolve(v, stack) for k, v in value.items()}
            elif key in ("items", "not"):
                result[key] = resolve(value, stack)
            elif key == "additionalProperties" and isinstance(value, dict):
                result[key] = resolve(value, stack)
            elif key in ("allOf", "anyOf", "oneOf") and isinstance(value, list):
                result[key] = [resolve(v, stack) for v in value]
            else:
                result[key] = copy.deepcopy(value)

        if schema.get("nullable") is True and isinstance(schema.get("type"), str):
            typ = schema["type"]
            result["type"] = [typ, "null"]

        return result

    def make_strict(schema, original_required=None):
        if isinstance(schema, list):
            for item in schema:
                make_strict(item)
            return
        if not isinstance(schema, dict):
            return

        properties = schema.get("properties")
        if isinstance(properties, dict):
            required_before = original_required
            if required_before is None:
                required_before = schema.get("required", [])
            required_set = set(required_before) if isinstance(required_before, list) else set()

            schema["additionalProperties"] = False
            schema["required"] = sorted(properties.keys())

            for name, child in properties.items():
                if name not in required_set and isinstance(child, dict):
                    typ = child.get("type")
                    if isinstance(typ, str) and typ != "null":
                        child["type"] = [typ, "null"]
                    elif isinstance(typ, list) and "null" not in typ:
                        child["type"] = typ + ["null"]
                    enum = child.get("enum")
                    if isinstance(enum, list) and None not in enum:
                        child["enum"] = enum + [None]

        for key in ("properties",):
            if isinstance(schema.get(key), dict):
                for child in schema[key].values():
                    make_strict(child)
        for key in ("items", "not"):
            if key in schema:
                make_strict(schema[key])
        if isinstance(schema.get("additionalProperties"), dict):
            make_strict(schema["additionalProperties"])
        for key in ("allOf", "anyOf", "oneOf"):
            if isinstance(schema.get(key), list):
                for child in schema[key]:
                    make_strict(child)

    result = {}
    for name, component in components.items():
        prepared = resolve(component, (name,))
        make_strict(prepared)
        result[name] = prepared
    return result