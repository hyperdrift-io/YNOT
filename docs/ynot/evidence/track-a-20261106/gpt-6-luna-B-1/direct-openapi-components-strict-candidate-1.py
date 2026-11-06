from copy import deepcopy


def transform(payload):
    components = payload["components"]["schemas"]

    def resolve(value):
        if isinstance(value, dict):
            ref = value.get("$ref")
            if isinstance(ref, str) and ref.startswith("#/components/schemas/"):
                name = ref[len("#/components/schemas/"):]
                return resolve(deepcopy(components[name]))
            return {key: resolve(child) if is_schema_child(key, child) else deepcopy(child)
                    for key, child in value.items()}
        if isinstance(value, list):
            return [resolve(item) for item in value]
        return deepcopy(value)

    def is_schema_child(key, child):
        return key in ("properties", "items", "additionalProperties", "not", "allOf", "anyOf", "oneOf")

    def walk_schema(schema, original_required=None):
        if not isinstance(schema, dict):
            return schema
        original_required = set(schema.get("required", [])) if original_required is None else original_required
        schema.pop("nullable", None)
        typ = schema.get("type")
        if schema.get("nullable") is True and isinstance(typ, str):
            schema["type"] = [typ, "null"]
        schema.pop("default", None)
        props = schema.get("properties")
        if isinstance(props, dict):
            for name, child in list(props.items()):
                was_required = name in original_required
                if isinstance(child, dict):
                    child = walk_schema(child)
                    props[name] = child
                    if not was_required:
                        t = child.get("type")
                        if isinstance(t, str) and t != "null":
                            child["type"] = [t, "null"]
                        elif isinstance(t, list) and "null" not in t:
                            child["type"] = t + ["null"]
                        enum = child.get("enum")
                        if isinstance(enum, list) and None not in enum:
                            child["enum"] = enum + [None]
            schema["additionalProperties"] = False
            schema["required"] = sorted(props)
        for key in ("items", "additionalProperties", "not"):
            child = schema.get(key)
            if isinstance(child, dict):
                schema[key] = walk_schema(child)
        for key in ("allOf", "anyOf", "oneOf"):
            children = schema.get(key)
            if isinstance(children, list):
                schema[key] = [walk_schema(child) for child in children]
        return schema

    prepared = {}
    for name, schema in components.items():
        resolved = resolve(schema)

        def nullability(node):
            if isinstance(node, dict):
                if node.get("nullable") is True and isinstance(node.get("type"), str):
                    node["type"] = [node["type"], "null"]
                node.pop("nullable", None)
                for key in ("properties", "items", "additionalProperties", "not", "allOf", "anyOf", "oneOf"):
                    child = node.get(key)
                    if key == "properties" and isinstance(child, dict):
                        for val in child.values():
                            nullability(val)
                    elif key in ("allOf", "anyOf", "oneOf") and isinstance(child, list):
                        for val in child:
                            nullability(val)
                    elif isinstance(child, dict):
                        nullability(child)
        nullability(resolved)
        prepared[name] = walk_schema(resolved)
    return prepared