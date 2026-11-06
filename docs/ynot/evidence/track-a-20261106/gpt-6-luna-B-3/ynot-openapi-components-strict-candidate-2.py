from copy import deepcopy

def transform(payload):
    components = payload["components"]["schemas"]

    def resolve(node):
        if isinstance(node, dict):
            ref = node.get("$ref")
            if isinstance(ref, str) and ref.startswith("#/components/schemas/"):
                name = ref[len("#/components/schemas/"):]
                return resolve(deepcopy(components[name]))
            out = {}
            for key, value in node.items():
                if key == "properties" and isinstance(value, dict):
                    out[key] = {name: resolve(child) for name, child in value.items()}
                elif key in ("items", "not") and isinstance(value, (dict, list)):
                    out[key] = resolve(value)
                elif key == "additionalProperties" and isinstance(value, dict):
                    out[key] = resolve(value)
                elif key in ("allOf", "anyOf", "oneOf") and isinstance(value, list):
                    out[key] = [resolve(child) for child in value]
                else:
                    out[key] = deepcopy(value)
            return out
        if isinstance(node, list):
            return [deepcopy(item) for item in node]
        return deepcopy(node)

    resolved = {name: resolve(schema) for name, schema in components.items()}

    def nullable_and_strict(node, original_required=None):
        if isinstance(node, list):
            return [nullable_and_strict(child) for child in node]
        if not isinstance(node, dict):
            return node

        required_before = original_required
        if required_before is None:
            required_before = node.get("required", [])
        props = node.get("properties")
        if isinstance(props, dict):
            for name, child in props.items():
                if name not in required_before and isinstance(child, dict):
                    typ = child.get("type")
                    if isinstance(typ, str) and typ != "null":
                        child["type"] = [typ, "null"]
                    elif isinstance(typ, list) and "null" not in typ:
                        child["type"] = typ + ["null"]
                    enum = child.get("enum")
                    if isinstance(enum, list) and None not in enum:
                        child["enum"] = enum + [None]
            node["additionalProperties"] = False
            node["required"] = sorted(props)

        node.pop("default", None)
        if node.pop("nullable", None) is True:
            typ = node.get("type")
            if isinstance(typ, str):
                node["type"] = [typ, "null"]

        for key, value in list(node.items()):
            if key == "properties" and isinstance(value, dict):
                for child in value.values():
                    nullable_and_strict(child)
            elif key in ("items", "not") and isinstance(value, (dict, list)):
                nullable_and_strict(value)
            elif key == "additionalProperties" and isinstance(value, dict):
                nullable_and_strict(value)
            elif key in ("allOf", "anyOf", "oneOf") and isinstance(value, list):
                nullable_and_strict(value)
        return node

    return {name: nullable_and_strict(schema) for name, schema in resolved.items()}