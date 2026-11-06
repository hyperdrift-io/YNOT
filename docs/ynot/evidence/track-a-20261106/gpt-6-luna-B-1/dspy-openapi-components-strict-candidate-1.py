import copy

def transform(payload):
    components = payload.get("components", {}).get("schemas", {})

    def resolve(schema):
        if isinstance(schema, dict):
            ref = schema.get("$ref")
            if isinstance(ref, str) and ref.startswith("#/components/schemas/"):
                name = ref[len("#/components/schemas/"):]
                if name in components:
                    return resolve(copy.deepcopy(components[name]))
            result = {}
            for key, value in schema.items():
                if key == "$ref":
                    result[key] = value
                elif key in ("properties",):
                    result[key] = {name: resolve(child) for name, child in value.items()}
                elif key in ("items", "additionalProperties", "not"):
                    result[key] = resolve(value) if isinstance(value, dict) else copy.deepcopy(value)
                elif key in ("allOf", "anyOf", "oneOf"):
                    result[key] = [resolve(child) for child in value]
                else:
                    result[key] = copy.deepcopy(value)
            return result
        return copy.deepcopy(schema)

    original_required = {}

    def snapshot_required(schema, path=()):
        if not isinstance(schema, dict):
            return
        if "properties" in schema:
            original_required[path] = set(schema.get("required", []))
            for name, child in schema["properties"].items():
                snapshot_required(child, path + ("properties", name))
        for key in ("items", "additionalProperties", "not"):
            child = schema.get(key)
            if isinstance(child, dict):
                snapshot_required(child, path + (key,))
        for key in ("allOf", "anyOf", "oneOf"):
            for i, child in enumerate(schema.get(key, [])):
                snapshot_required(child, path + (key, i))

    def nullable(schema):
        if not isinstance(schema, dict):
            return
        if schema.get("nullable") is True and isinstance(schema.get("type"), str):
            schema["type"] = [schema["type"], "null"]
        schema.pop("nullable", None)
        for child in children(schema):
            nullable(child)

    def children(schema):
        for child in schema.get("properties", {}).values() if isinstance(schema.get("properties"), dict) else ():
            yield child
        for key in ("items", "additionalProperties", "not"):
            child = schema.get(key)
            if isinstance(child, dict):
                yield child
        for key in ("allOf", "anyOf", "oneOf"):
            value = schema.get(key)
            if isinstance(value, list):
                yield from value

    def strict(schema, path=()):
        if not isinstance(schema, dict):
            return
        schema.pop("default", None)
        if isinstance(schema.get("properties"), dict):
            required_before = original_required.get(path, set())
            schema["additionalProperties"] = False
            schema["required"] = sorted(schema["properties"])
            for name, child in schema["properties"].items():
                if name not in required_before and isinstance(child, dict):
                    typ = child.get("type")
                    if isinstance(typ, str) and typ != "null":
                        child["type"] = [typ, "null"]
                    elif isinstance(typ, list) and "null" not in typ:
                        child["type"] = typ + ["null"]
                    enum = child.get("enum")
                    if isinstance(enum, list) and None not in enum:
                        child["enum"] = enum + [None]
                strict(child, path + ("properties", name))
        for key in ("items", "additionalProperties", "not"):
            child = schema.get(key)
            if isinstance(child, dict):
                strict(child, path + (key,))
        for key in ("allOf", "anyOf", "oneOf"):
            value = schema.get(key)
            if isinstance(value, list):
                for i, child in enumerate(value):
                    strict(child, path + (key, i))

    prepared = {}
    for name, component in components.items():
        resolved = resolve(component)
        snapshot_required(resolved, (name,))
        nullable(resolved)
        strict(resolved, (name,))
        prepared[name] = resolved
    return prepared