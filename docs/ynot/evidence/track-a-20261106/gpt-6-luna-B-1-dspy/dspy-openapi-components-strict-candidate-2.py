def transform(payload):
    import copy

    components = payload.get("components", {}).get("schemas", {})

    def resolve(value):
        if isinstance(value, list):
            return [resolve(item) for item in value]
        if not isinstance(value, dict):
            return copy.deepcopy(value)

        ref = value.get("$ref")
        prefix = "#/components/schemas/"
        if isinstance(ref, str) and ref.startswith(prefix):
            name = ref[len(prefix):]
            if name not in components:
                raise KeyError(name)
            return resolve(components[name])

        schema_keys = {
            "properties", "items", "additionalProperties", "not",
            "allOf", "anyOf", "oneOf",
        }
        return {
            key: resolve(child) if key in schema_keys else copy.deepcopy(child)
            for key, child in value.items()
        }

    def nullable_stage(schema):
        if isinstance(schema, list):
            return [nullable_stage(item) for item in schema]
        if not isinstance(schema, dict):
            return schema

        result = {}
        for key, value in schema.items():
            if key == "nullable":
                continue
            if key == "properties" and isinstance(value, dict):
                result[key] = {name: nullable_stage(prop) for name, prop in value.items()}
            elif key in {"items", "additionalProperties", "not"} and isinstance(value, dict):
                result[key] = nullable_stage(value)
            elif key in {"allOf", "anyOf", "oneOf"} and isinstance(value, list):
                result[key] = [nullable_stage(member) for member in value]
            else:
                result[key] = copy.deepcopy(value)

        if schema.get("nullable") is True and isinstance(schema.get("type"), str):
            result["type"] = [schema["type"], "null"]
        return result

    def strict_stage(schema):
        if isinstance(schema, list):
            return [strict_stage(item) for item in schema]
        if not isinstance(schema, dict):
            return schema

        original_required = schema.get("required", [])
        properties = schema.get("properties")
        result = {}
        for key, value in schema.items():
            if key == "default":
                continue
            if key == "properties" and isinstance(value, dict):
                result[key] = {name: strict_stage(prop) for name, prop in value.items()}
            elif key in {"items", "additionalProperties", "not"} and isinstance(value, dict):
                result[key] = strict_stage(value)
            elif key in {"allOf", "anyOf", "oneOf"} and isinstance(value, list):
                result[key] = [strict_stage(member) for member in value]
            else:
                result[key] = copy.deepcopy(value)

        if isinstance(properties, dict):
            names = sorted(properties)
            result["additionalProperties"] = False
            result["required"] = names
            for name in names:
                if name in original_required:
                    continue
                prop = result["properties"][name]
                if not isinstance(prop, dict):
                    continue
                typ = prop.get("type")
                if isinstance(typ, str) and typ != "null":
                    prop["type"] = [typ, "null"]
                elif isinstance(typ, list) and "null" not in typ:
                    prop["type"] = typ + ["null"]
                enum = prop.get("enum")
                if isinstance(enum, list) and None not in enum:
                    prop["enum"] = enum + [None]
        return result

    return {
        name: strict_stage(nullable_stage(resolve(component)))
        for name, component in components.items()
    }