def transform(payload):
    import copy

    components = payload.get("components", {}).get("schemas", {})

    def walk(value, active=()):
        if isinstance(value, list):
            return [walk(item, active) for item in value]
        if not isinstance(value, dict):
            return copy.deepcopy(value)

        ref = value.get("$ref")
        prefix = "#/components/schemas/"
        if isinstance(ref, str) and ref.startswith(prefix):
            name = ref[len(prefix):]
            if name not in components or name in active:
                raise ValueError("Invalid component reference")
            return walk(components[name], active + (name,))

        result = {}
        nullable = value.get("nullable") is True
        for key, item in value.items():
            if key in ("nullable", "default"):
                continue
            if key == "properties" and isinstance(item, dict):
                result[key] = {prop: walk(child, active) for prop, child in item.items()}
            elif key in ("items", "not"):
                result[key] = walk(item, active)
            elif key == "additionalProperties" and isinstance(item, dict):
                result[key] = walk(item, active)
            elif key in ("allOf", "anyOf", "oneOf") and isinstance(item, list):
                result[key] = [walk(child, active) for child in item]
            else:
                result[key] = copy.deepcopy(item)

        if nullable and isinstance(value.get("type"), str):
            result["type"] = [value["type"], "null"]
        return result

    def prepare(schema):
        if isinstance(schema, list):
            for child in schema:
                prepare(child)
            return
        if not isinstance(schema, dict):
            return

        properties = schema.get("properties")
        if isinstance(properties, dict):
            original_required = schema.get("required", [])
            required = set(original_required) if isinstance(original_required, list) else set()
            schema["additionalProperties"] = False
            schema["required"] = sorted(properties)
            for name, child in properties.items():
                if name in required or not isinstance(child, dict):
                    continue
                typ = child.get("type")
                if isinstance(typ, str) and typ != "null":
                    child["type"] = [typ, "null"]
                elif isinstance(typ, list) and "null" not in typ:
                    child["type"] = typ + ["null"]
                enum = child.get("enum")
                if isinstance(enum, list) and None not in enum:
                    child["enum"] = enum + [None]

        if isinstance(properties, dict):
            for child in properties.values():
                prepare(child)
        for key in ("items", "not"):
            if key in schema:
                prepare(schema[key])
        if isinstance(schema.get("additionalProperties"), dict):
            prepare(schema["additionalProperties"])
        for key in ("allOf", "anyOf", "oneOf"):
            value = schema.get(key)
            if isinstance(value, list):
                for child in value:
                    prepare(child)

    result = {}
    for name, component in components.items():
        schema = walk(component, (name,))
        prepare(schema)
        result[name] = schema
    return result