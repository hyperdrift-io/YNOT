from copy import deepcopy


def transform(payload):
    components = payload["components"]["schemas"]
    schema_keys = {"properties", "items", "additionalProperties", "not", "allOf", "anyOf", "oneOf"}
    prefix = "#/components/schemas/"

    def resolve(node):
        if isinstance(node, dict):
            ref = node.get("$ref")
            if isinstance(ref, str) and ref.startswith(prefix):
                name = ref[len(prefix):]
                return resolve(deepcopy(components[name]))
            out = {}
            for key, value in node.items():
                if key == "properties" and isinstance(value, dict):
                    out[key] = {name: resolve(child) for name, child in value.items()}
                elif key in ("items", "additionalProperties", "not") and isinstance(value, dict):
                    out[key] = resolve(value)
                elif key in ("allOf", "anyOf", "oneOf") and isinstance(value, list):
                    out[key] = [resolve(child) for child in value]
                else:
                    out[key] = deepcopy(value)
            return out
        return deepcopy(node)

    def prepare(schema):
        if not isinstance(schema, dict):
            return schema

        original_required = set(schema.get("required", []))
        typ = schema.get("type")
        if schema.get("nullable") is True and isinstance(typ, str):
            schema["type"] = [typ, "null"]
        schema.pop("nullable", None)
        schema.pop("default", None)

        props = schema.get("properties")
        if isinstance(props, dict):
            for name, child in list(props.items()):
                child = prepare(child)
                props[name] = child
                if name not in original_required and isinstance(child, dict):
                    typ = child.get("type")
                    if isinstance(typ, str) and typ != "null":
                        child["type"] = [typ, "null"]
                    elif isinstance(typ, list) and "null" not in typ:
                        child["type"] = typ + ["null"]
                    enum = child.get("enum")
                    if isinstance(enum, list) and None not in enum:
                        child["enum"] = enum + [None]
            schema["additionalProperties"] = False
            schema["required"] = sorted(props)

        for key in ("items", "additionalProperties", "not"):
            child = schema.get(key)
            if isinstance(child, dict):
                schema[key] = prepare(child)
        for key in ("allOf", "anyOf", "oneOf"):
            children = schema.get(key)
            if isinstance(children, list):
                schema[key] = [prepare(child) for child in children]
        return schema

    return {name: prepare(resolve(schema)) for name, schema in components.items()}