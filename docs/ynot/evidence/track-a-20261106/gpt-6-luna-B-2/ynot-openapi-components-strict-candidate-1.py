from copy import deepcopy


def transform(payload):
    components = payload["components"]["schemas"]

    def resolve(schema):
        if not isinstance(schema, dict):
            return deepcopy(schema)
        ref = schema.get("$ref")
        if isinstance(ref, str) and ref.startswith("#/components/schemas/"):
            name = ref[len("#/components/schemas/"):]
            return resolve(components[name])
        result = deepcopy(schema)
        for key, value in list(result.items()):
            if key == "properties" and isinstance(value, dict):
                result[key] = {name: resolve(child) for name, child in value.items()}
            elif key in ("items", "additionalProperties", "not") and isinstance(value, dict):
                result[key] = resolve(value)
            elif key in ("allOf", "anyOf", "oneOf") and isinstance(value, list):
                result[key] = [resolve(child) for child in value]
        return result

    resolved = {name: resolve(schema) for name, schema in components.items()}
    original_required = {}

    def capture(schema, path=()):
        if not isinstance(schema, dict):
            return
        original_required[path] = set(schema.get("required", []))
        props = schema.get("properties")
        if isinstance(props, dict):
            for name, child in props.items():
                capture(child, path + ("properties", name))
        for key in ("items", "additionalProperties", "not"):
            child = schema.get(key)
            if isinstance(child, dict):
                capture(child, path + (key,))
        for key in ("allOf", "anyOf", "oneOf"):
            children = schema.get(key)
            if isinstance(children, list):
                for index, child in enumerate(children):
                    capture(child, path + (key, index))

    for name, schema in resolved.items():
        capture(schema, (name,))

    def prepare(schema, parent_required=None, path=()):
        if not isinstance(schema, dict):
            return schema
        schema.pop("default", None)
        nullable = schema.pop("nullable", None)
        if nullable is True and isinstance(schema.get("type"), str):
            schema["type"] = [schema["type"], "null"]
        if parent_required is not None:
            prop_type = schema.get("type")
            if isinstance(prop_type, str) and prop_type != "null":
                schema["type"] = [prop_type, "null"]
            elif isinstance(prop_type, list) and "null" not in prop_type:
                prop_type.append("null")
            enum = schema.get("enum")
            if isinstance(enum, list) and None not in enum:
                enum.append(None)
        props = schema.get("properties")
        if isinstance(props, dict):
            required = original_required.get(path, set())
            schema["additionalProperties"] = False
            schema["required"] = sorted(props)
            for name, child in props.items():
                prepare(child, name in required, path + ("properties", name))
        for key in ("items", "additionalProperties", "not"):
            child = schema.get(key)
            if isinstance(child, dict):
                prepare(child, None, path + (key,))
        for key in ("allOf", "anyOf", "oneOf"):
            children = schema.get(key)
            if isinstance(children, list):
                for index, child in enumerate(children):
                    prepare(child, None, path + (key, index))
        return schema

    return {name: prepare(schema, None, (name,)) for name, schema in resolved.items()}
