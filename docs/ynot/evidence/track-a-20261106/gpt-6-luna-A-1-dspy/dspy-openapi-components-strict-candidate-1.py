def transform(payload):
    import copy

    components = payload.get("components", {}).get("schemas", {})
    prepared = {}

    def resolve(value):
        if isinstance(value, dict):
            ref = value.get("$ref")
            if isinstance(ref, str) and ref.startswith("#/components/schemas/"):
                name = ref[len("#/components/schemas/"):]
                return resolve(copy.deepcopy(components[name]))
            return {key: resolve(child) for key, child in value.items()}
        if isinstance(value, list):
            return [resolve(child) for child in value]
        return copy.deepcopy(value)

    def schema_children(schema):
        for key in ("properties",):
            value = schema.get(key)
            if isinstance(value, dict):
                for child in value.values():
                    yield child
        for key in ("items", "not"):
            if key in schema:
                yield schema[key]
        value = schema.get("additionalProperties")
        if isinstance(value, dict):
            yield value
        for key in ("allOf", "anyOf", "oneOf"):
            value = schema.get(key)
            if isinstance(value, list):
                yield from value

    def nullable_walk(schema):
        if isinstance(schema, list):
            for child in schema:
                nullable_walk(child)
            return
        if not isinstance(schema, dict):
            return
        if schema.get("nullable") is True and isinstance(schema.get("type"), str):
            schema["type"] = [schema["type"], "null"]
        schema.pop("nullable", None)
        for child in schema_children(schema):
            nullable_walk(child)

    def strict_walk(schema, original_required):
        if isinstance(schema, list):
            for child in schema:
                strict_walk(child, set())
            return
        if not isinstance(schema, dict):
            return

        properties = schema.get("properties")
        if isinstance(properties, dict):
            required = schema.get("required")
            parent_required = set(original_required if original_required is not None else
                                  (required if isinstance(required, list) else []))
            names = sorted(properties)
            schema["additionalProperties"] = False
            schema["required"] = names
            for name, child in properties.items():
                if name not in parent_required and isinstance(child, dict):
                    typ = child.get("type")
                    if isinstance(typ, str) and typ != "null":
                        child["type"] = [typ, "null"]
                    elif isinstance(typ, list) and "null" not in typ:
                        typ.append("null")
                    enum = child.get("enum")
                    if isinstance(enum, list) and None not in enum:
                        enum.append(None)

        for child in schema_children(schema):
            strict_walk(child, None)

        schema.pop("default", None)

    for name, component in components.items():
        schema = resolve(copy.deepcopy(component))
        nullable_walk(schema)
        strict_walk(schema, None)
        prepared[name] = schema

    return prepared