from copy import deepcopy


def transform(payload):
    components = payload["components"]["schemas"]
    roots = deepcopy(components)

    def resolve(schema):
        if isinstance(schema, dict):
            ref = schema.get("$ref")
            if isinstance(ref, str) and ref.startswith("#/components/schemas/"):
                name = ref[len("#/components/schemas/"):]
                if "/" not in name:
                    return resolve(deepcopy(roots[name]))
            for key, value in list(schema.items()):
                if key in ("properties", "additionalProperties") and isinstance(value, dict):
                    if key == "properties":
                        schema[key] = {k: resolve(v) for k, v in value.items()}
                    else:
                        schema[key] = resolve(value)
                elif key in ("items", "not") and isinstance(value, dict):
                    schema[key] = resolve(value)
                elif key in ("allOf", "anyOf", "oneOf") and isinstance(value, list):
                    schema[key] = [resolve(v) for v in value]
            if isinstance(ref, str) and ref.startswith("#/components/schemas/"):
                name = ref[len("#/components/schemas/"):]
                if "/" not in name:
                    return resolve(deepcopy(roots[name]))
        return schema

    resolved = {name: resolve(deepcopy(schema)) for name, schema in roots.items()}

    def walk(schema, parent_required=None, property_name=None):
        if not isinstance(schema, dict):
            return schema
        schema.pop("nullable", None)
        if schema.get("nullable") is True:
            pass
        # Nullable is applied before removal semantics, using the original value.
        # (Handled by retaining it during the operation below.)
        return schema

    def prepare(schema, optional=False):
        if not isinstance(schema, dict):
            return schema
        nullable = schema.pop("nullable", None)
        if nullable is True and isinstance(schema.get("type"), str):
            schema["type"] = [schema["type"], "null"]
        schema.pop("default", None)

        props = schema.get("properties")
        if isinstance(props, dict):
            original_required = schema.get("required", [])
            if not isinstance(original_required, list):
                original_required = []
            schema["additionalProperties"] = False
            schema["required"] = sorted(props.keys())
            for name, child in list(props.items()):
                child_optional = name not in original_required
                if isinstance(child, dict) and child_optional:
                    typ = child.get("type")
                    if isinstance(typ, str) and typ != "null":
                        child["type"] = [typ, "null"]
                    elif isinstance(typ, list) and "null" not in typ:
                        child["type"] = typ + ["null"]
                    enum = child.get("enum")
                    if isinstance(enum, list) and None not in enum:
                        child["enum"] = enum + [None]
                props[name] = prepare(child)

        for key in ("items", "not"):
            if isinstance(schema.get(key), dict):
                schema[key] = prepare(schema[key])
        ap = schema.get("additionalProperties")
        if isinstance(ap, dict):
            schema["additionalProperties"] = prepare(ap)
        for key in ("allOf", "anyOf", "oneOf"):
            if isinstance(schema.get(key), list):
                schema[key] = [prepare(item) for item in schema[key]]
        return schema

    return {name: prepare(schema) for name, schema in resolved.items()}