def transform(payload):
    import copy

    components = payload.get("components", {}).get("schemas", {})
    original = copy.deepcopy(components)

    def resolve(schema):
        if isinstance(schema, dict):
            ref = schema.get("$ref")
            if isinstance(ref, str) and ref.startswith("#/components/schemas/"):
                name = ref[len("#/components/schemas/"):]
                if name in original:
                    return resolve(copy.deepcopy(original[name]))
            result = {}
            for key, value in schema.items():
                if key == "$ref":
                    result[key] = value
                elif key in ("properties",):
                    result[key] = {k: resolve(v) for k, v in value.items()} if isinstance(value, dict) else copy.deepcopy(value)
                elif key in ("items", "not"):
                    result[key] = resolve(value)
                elif key == "additionalProperties" and isinstance(value, dict):
                    result[key] = resolve(value)
                elif key in ("allOf", "anyOf", "oneOf") and isinstance(value, list):
                    result[key] = [resolve(v) for v in value]
                else:
                    result[key] = copy.deepcopy(value)
            return result
        if isinstance(schema, list):
            return [resolve(v) for v in schema]
        return copy.deepcopy(schema)

    def prepare(schema, parent_required=None, property_name=None):
        if isinstance(schema, list):
            return [prepare(v) for v in schema]
        if not isinstance(schema, dict):
            return schema

        result = {k: copy.deepcopy(v) for k, v in schema.items()}
        nullable = result.pop("nullable", None)
        if nullable is True and isinstance(result.get("type"), str):
            result["type"] = [result["type"], "null"]

        props = result.get("properties")
        if isinstance(props, dict):
            original_required = schema.get("required", [])
            required_set = set(original_required) if isinstance(original_required, list) else set()
            prepared_props = {}
            for name, value in props.items():
                child = prepare(value)
                if name not in required_set and isinstance(child, dict):
                    typ = child.get("type")
                    if isinstance(typ, str) and typ != "null":
                        child["type"] = [typ, "null"]
                    elif isinstance(typ, list) and "null" not in typ:
                        child["type"] = typ + ["null"]
                    elif "type" not in child:
                        enum = child.get("enum")
                        if isinstance(enum, list) and None not in enum:
                            child["enum"] = enum + [None]
                prepared_props[name] = child
            result["properties"] = prepared_props
            result["additionalProperties"] = False
            result["required"] = sorted(props)

        for key in ("items", "not"):
            if key in result:
                result[key] = prepare(result[key])
        if isinstance(result.get("additionalProperties"), dict):
            result["additionalProperties"] = prepare(result["additionalProperties"])
        for key in ("allOf", "anyOf", "oneOf"):
            if isinstance(result.get(key), list):
                result[key] = [prepare(v) for v in result[key]]

        result.pop("default", None)
        return result

    return {name: prepare(resolve(schema)) for name, schema in original.items()}