def transform(payload):
    import copy

    schemas = payload.get("components", {}).get("schemas", {})
    original_required = {
        name: set(schema.get("required", []))
        for name, schema in schemas.items()
        if isinstance(schema, dict)
    }

    def resolve(node):
        if isinstance(node, dict):
            ref = node.get("$ref")
            if isinstance(ref, str) and ref.startswith("#/components/schemas/"):
                name = ref[len("#/components/schemas/"):]
                if name in schemas:
                    return resolve(copy.deepcopy(schemas[name]))

            result = copy.deepcopy(node)
            result.pop("$ref", None) if isinstance(ref, str) and ref.startswith("#/components/schemas/") else None
            for key in ("properties",):
                value = node.get(key)
                if isinstance(value, dict):
                    result[key] = {k: resolve(v) for k, v in value.items()}
            for key in ("items", "not", "additionalProperties"):
                value = node.get(key)
                if isinstance(value, dict):
                    result[key] = resolve(value)
            for key in ("allOf", "anyOf", "oneOf"):
                value = node.get(key)
                if isinstance(value, list):
                    result[key] = [resolve(v) for v in value]
            return result
        if isinstance(node, list):
            return [resolve(v) for v in node]
        return copy.deepcopy(node)

    def prepare(node, required_names):
        if isinstance(node, dict):
            result = copy.deepcopy(node)

            for key, value in list(node.items()):
                if key == "properties" and isinstance(value, dict):
                    result[key] = {
                        name: prepare(child, set())
                        for name, child in value.items()
                    }
                elif key in ("items", "not", "additionalProperties") and isinstance(value, dict):
                    result[key] = prepare(value, set())
                elif key in ("allOf", "anyOf", "oneOf") and isinstance(value, list):
                    result[key] = [prepare(child, set()) for child in value]

            if node.get("nullable") is True and isinstance(node.get("type"), str):
                result["type"] = [node["type"], "null"]
            result.pop("nullable", None)
            result.pop("default", None)

            props = node.get("properties")
            if isinstance(props, dict):
                result["additionalProperties"] = False
                result["required"] = sorted(props)
                for name, child in result["properties"].items():
                    if name not in required_names and isinstance(child, dict):
                        typ = child.get("type")
                        if isinstance(typ, str) and typ != "null":
                            child["type"] = [typ, "null"]
                        elif isinstance(typ, list) and "null" not in typ:
                            child["type"] = typ + ["null"]
                        enum = child.get("enum")
                        if isinstance(enum, list) and None not in enum:
                            child["enum"] = enum + [None]
            return result
        if isinstance(node, list):
            return [prepare(child, set()) for child in node]
        return copy.deepcopy(node)

    output = {}
    for name, schema in schemas.items():
        resolved = resolve(copy.deepcopy(schema))
        output[name] = prepare(resolved, original_required.get(name, set()))
    return output