from copy import deepcopy


def transform(payload):
    components = payload["components"]["schemas"]

    def resolve(node):
        if isinstance(node, list):
            return [resolve(value) for value in node]
        if not isinstance(node, dict):
            return deepcopy(node)
        ref = node.get("$ref")
        if isinstance(ref, str) and ref.startswith("#/components/schemas/"):
            name = ref[len("#/components/schemas/"):]
            return resolve(deepcopy(components[name]))
        return {key: resolve(value) if key in _SCHEMA_KEYS else deepcopy(value)
                for key, value in node.items()}

    def prepare(node, original_required=None):
        if isinstance(node, list):
            return [prepare(value) for value in node]
        if not isinstance(node, dict):
            return node

        result = deepcopy(node)
        nullable = result.pop("nullable", None)
        if nullable is True and isinstance(result.get("type"), str):
            result["type"] = [result["type"], "null"]

        properties = result.get("properties")
        if isinstance(properties, dict):
            required = set(original_required or [])
            result["additionalProperties"] = False
            result["required"] = sorted(properties)
            for name, child in properties.items():
                properties[name] = prepare(child)
                if name not in required:
                    typ = properties[name].get("type") if isinstance(properties[name], dict) else None
                    if isinstance(typ, str) and typ != "null":
                        properties[name]["type"] = [typ, "null"]
                    elif isinstance(typ, list) and "null" not in typ:
                        properties[name]["type"] = typ + ["null"]
                    enum = properties[name].get("enum")
                    if isinstance(enum, list) and None not in enum:
                        properties[name]["enum"] = enum + [None]
        for key in _CHILD_SCHEMA_KEYS:
            if key in result:
                value = result[key]
                if key in ("allOf", "anyOf", "oneOf") and isinstance(value, list):
                    result[key] = [prepare(item) for item in value]
                elif isinstance(value, dict):
                    result[key] = prepare(value)
        result.pop("default", None)
        return result

    _ = None
    resolved = {name: resolve(schema) for name, schema in components.items()}
    return {name: _prepare_root(schema) for name, schema in resolved.items()}


_SCHEMA_KEYS = {
    "properties", "items", "additionalProperties", "not", "allOf", "anyOf", "oneOf"
}
_CHILD_SCHEMA_KEYS = {"items", "additionalProperties", "not", "allOf", "anyOf", "oneOf"}


def _prepare_root(schema):
    def walk(node, parent_required=None):
        if isinstance(node, list):
            return [walk(item) for item in node]
        if not isinstance(node, dict):
            return node
        result = deepcopy(node)
        result.pop("default", None)
        if result.pop("nullable", None) is True and isinstance(result.get("type"), str):
            result["type"] = [result["type"], "null"]
        props = result.get("properties")
        if isinstance(props, dict):
            old_required = set(result.get("required", []))
            result["required"] = sorted(props)
            result["additionalProperties"] = False
            for name, child in list(props.items()):
                child = walk(child)
                if name not in old_required and isinstance(child, dict):
                    typ = child.get("type")
                    if isinstance(typ, str) and typ != "null":
                        child["type"] = [typ, "null"]
                    elif isinstance(typ, list) and "null" not in typ:
                        child["type"] = typ + ["null"]
                    enum = child.get("enum")
                    if isinstance(enum, list) and None not in enum:
                        child["enum"] = enum + [None]
                props[name] = child
        for key in _CHILD_SCHEMA_KEYS:
            val = result.get(key)
            if isinstance(val, dict):
                result[key] = walk(val)
            elif key in ("allOf", "anyOf", "oneOf") and isinstance(val, list):
                result[key] = [walk(item) for item in val]
        return result
    return walk(schema)
