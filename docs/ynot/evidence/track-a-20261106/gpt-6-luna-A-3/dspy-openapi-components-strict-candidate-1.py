def transform(payload):
    import copy

    schemas = payload.get("components", {}).get("schemas", {})
    original_required = {
        name: set(schema.get("required", []))
        for name, schema in schemas.items()
        if isinstance(schema, dict)
    }

    def walk(node, resolve=True):
        if isinstance(node, dict):
            ref = node.get("$ref")
            if resolve and isinstance(ref, str) and ref.startswith("#/components/schemas/"):
                name = ref[len("#/components/schemas/"):]
                if name in schemas:
                    return walk(copy.deepcopy(schemas[name]), resolve=True)

            result = {}
            for key, value in node.items():
                if key == "nullable":
                    continue
                if key in ("properties",) and isinstance(value, dict):
                    result[key] = {k: walk(v) for k, v in value.items()}
                elif key in ("items", "not") and isinstance(value, dict):
                    result[key] = walk(value)
                elif key == "additionalProperties" and isinstance(value, dict):
                    result[key] = walk(value)
                elif key in ("allOf", "anyOf", "oneOf") and isinstance(value, list):
                    result[key] = [walk(v) for v in value]
                else:
                    result[key] = copy.deepcopy(value)

            typ = node.get("type")
            if node.get("nullable") is True and isinstance(typ, str):
                result["type"] = [typ, "null"]

            if "properties" in result and isinstance(result["properties"], dict):
                result["additionalProperties"] = False
                result["required"] = sorted(result["properties"])

            result.pop("default", None)
            return result
        if isinstance(node, list):
            return [walk(v) for v in node]
        return copy.deepcopy(node)

    prepared = {}
    for name, schema in schemas.items():
        item = walk(copy.deepcopy(schema))
        required = original_required.get(name, set())

        def mark_optional(node, is_root=False):
            if isinstance(node, dict):
                props = node.get("properties")
                if isinstance(props, dict):
                    for key, child in props.items():
                        if key not in required:
                            if isinstance(child, dict):
                                typ = child.get("type")
                                if isinstance(typ, str) and typ != "null":
                                    child["type"] = [typ, "null"]
                                elif isinstance(typ, list) and "null" not in typ:
                                    child["type"] = typ + ["null"]
                                enum = child.get("enum")
                                if isinstance(enum, list) and None not in enum:
                                    child["enum"] = enum + [None]
                        mark_optional(child)
                for key in ("items", "not", "additionalProperties"):
                    if key in node:
                        mark_optional(node[key])
                for key in ("allOf", "anyOf", "oneOf"):
                    for child in node.get(key, []) if isinstance(node.get(key), list) else []:
                        mark_optional(child)
            elif isinstance(node, list):
                for child in node:
                    mark_optional(child)

        mark_optional(item, True)
        prepared[name] = item
    return prepared