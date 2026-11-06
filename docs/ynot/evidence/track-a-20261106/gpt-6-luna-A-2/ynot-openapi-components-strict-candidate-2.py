from copy import deepcopy


def transform(payload):
    components = payload["components"]["schemas"]
    schema_keys = {"properties", "items", "additionalProperties", "not", "allOf", "anyOf", "oneOf"}

    def resolve(node):
        if isinstance(node, list):
            return [resolve(item) for item in node]
        if not isinstance(node, dict):
            return deepcopy(node)
        ref = node.get("$ref")
        if isinstance(ref, str) and ref.startswith("#/components/schemas/"):
            name = ref[len("#/components/schemas/"):]
            return resolve(deepcopy(components[name]))
        result = deepcopy(node)
        for key in schema_keys:
            if key not in result:
                continue
            value = result[key]
            if key == "properties" and isinstance(value, dict):
                result[key] = {name: resolve(child) for name, child in value.items()}
            elif key in {"allOf", "anyOf", "oneOf"} and isinstance(value, list):
                result[key] = [resolve(child) for child in value]
            elif isinstance(value, (dict, list)):
                result[key] = resolve(value)
        return result

    def prepare(node, parent_required=None):
        if isinstance(node, list):
            return [prepare(item) for item in node]
        if not isinstance(node, dict):
            return node
        result = deepcopy(node)
        result.pop("default", None)
        if result.pop("nullable", None) is True and isinstance(result.get("type"), str):
            result["type"] = [result["type"], "null"]

        properties = result.get("properties")
        if isinstance(properties, dict):
            original_required = set(result.get("required", []))
            result["required"] = sorted(properties)
            result["additionalProperties"] = False
            prepared = {}
            for name, child in properties.items():
                child = prepare(child)
                if name not in original_required and isinstance(child, dict):
                    typ = child.get("type")
                    if isinstance(typ, str) and typ != "null":
                        child["type"] = [typ, "null"]
                    elif isinstance(typ, list) and "null" not in typ:
                        child["type"] = typ + ["null"]
                    enum = child.get("enum")
                    if isinstance(enum, list) and None not in enum:
                        child["enum"] = enum + [None]
                prepared[name] = child
            result["properties"] = prepared

        for key in schema_keys - {"properties"}:
            if key not in result:
                continue
            value = result[key]
            if key in {"allOf", "anyOf", "oneOf"} and isinstance(value, list):
                result[key] = [prepare(child) for child in value]
            elif isinstance(value, (dict, list)):
                result[key] = prepare(value)
        return result

    return {name: prepare(resolve(schema)) for name, schema in components.items()}