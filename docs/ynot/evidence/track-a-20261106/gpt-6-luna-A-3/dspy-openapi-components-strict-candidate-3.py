def transform(payload):
    import copy

    schemas = payload.get("components", {}).get("schemas", {})
    original_required = {
        name: set(schema.get("required", []))
        for name, schema in schemas.items()
        if isinstance(schema, dict) and isinstance(schema.get("required", []), list)
    }

    def resolve(node):
        if isinstance(node, dict):
            ref = node.get("$ref")
            if isinstance(ref, str) and ref.startswith("#/components/schemas/"):
                name = ref[len("#/components/schemas/"):]
                if name in schemas:
                    return resolve(copy.deepcopy(schemas[name]))

            result = {}
            for key, value in node.items():
                if key == "$ref" and isinstance(ref, str) and ref.startswith("#/components/schemas/"):
                    continue
                if key == "properties" and isinstance(value, dict):
                    result[key] = {k: resolve(v) for k, v in value.items()}
                elif key in ("items", "not") and isinstance(value, dict):
                    result[key] = resolve(value)
                elif key == "additionalProperties" and isinstance(value, dict):
                    result[key] = resolve(value)
                elif key in ("allOf", "anyOf", "oneOf") and isinstance(value, list):
                    result[key] = [resolve(v) for v in value]
                else:
                    result[key] = copy.deepcopy(value)
            return result
        if isinstance(node, list):
            return [resolve(value) for value in node]
        return copy.deepcopy(node)

    def prepare(node, required_names=frozenset()):
        if isinstance(node, dict):
            result = {}
            for key, value in node.items():
                if key == "nullable":
                    continue
                if key == "default":
                    continue
                if key == "properties" and isinstance(value, dict):
                    result[key] = {
                        name: prepare(child, required_names=set())
                        for name, child in value.items()
                    }
                elif key in ("items", "not") and isinstance(value, dict):
                    result[key] = prepare(value)
                elif key == "additionalProperties" and isinstance(value, dict):
                    result[key] = prepare(value)
                elif key in ("allOf", "anyOf", "oneOf") and isinstance(value, list):
                    result[key] = [prepare(child) for child in value]
                else:
                    result[key] = copy.deepcopy(value)

            typ = node.get("type")
            if node.get("nullable") is True and isinstance(typ, str):
                result["type"] = [typ, "null"]

            props = node.get("properties")
            if isinstance(props, dict):
                result["additionalProperties"] = False
                result["required"] = sorted(props)
                original = set(node.get("required", [])) if isinstance(node.get("required", []), list) else set()
                for name, child in result["properties"].items():
                    if name in original or not isinstance(child, dict):
                        continue
                    child_type = child.get("type")
                    if isinstance(child_type, str) and child_type != "null":
                        child["type"] = [child_type, "null"]
                    elif isinstance(child_type, list) and "null" not in child_type:
                        child["type"] = child_type + ["null"]
                    enum = child.get("enum")
                    if isinstance(enum, list) and None not in enum:
                        child["enum"] = enum + [None]
            return result
        if isinstance(node, list):
            return [prepare(value) for value in node]
        return copy.deepcopy(node)

    return {
        name: prepare(resolve(copy.deepcopy(schema)), original_required.get(name, set()))
        for name, schema in schemas.items()
    }