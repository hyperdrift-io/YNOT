from copy import deepcopy


def transform(payload):
    components = payload["components"]["schemas"]

    def resolve(value):
        if isinstance(value, dict):
            ref = value.get("$ref")
            if isinstance(ref, str) and ref.startswith("#/components/schemas/"):
                name = ref[len("#/components/schemas/"):]
                return resolve(components[name])
            return {
                key: resolve(child) if key in ("properties", "items", "additionalProperties", "not", "allOf", "anyOf", "oneOf") else deepcopy(child)
                for key, child in value.items()
            } if False else _resolve_schema(value)
        if isinstance(value, list):
            return [resolve(child) for child in value]
        return deepcopy(value)

    schema_keys = {"properties", "items", "additionalProperties", "not", "allOf", "anyOf", "oneOf"}

    def _resolve_schema(schema):
        result = {}
        for key, value in schema.items():
            if key == "properties" and isinstance(value, dict):
                result[key] = {name: resolve(child) for name, child in value.items()}
            elif key in ("items", "additionalProperties", "not") and isinstance(value, dict):
                result[key] = resolve(value)
            elif key in ("allOf", "anyOf", "oneOf") and isinstance(value, list):
                result[key] = [resolve(child) for child in value]
            else:
                result[key] = deepcopy(value)
        return result

    resolved = {name: resolve(schema) for name, schema in components.items()}

    def prepare(schema, parent_required=True):
        if not isinstance(schema, dict):
            return schema
        schema.pop("default", None)
        nullable = schema.pop("nullable", None)
        if nullable is True and isinstance(schema.get("type"), str):
            schema["type"] = [schema["type"], "null"]

        if not parent_required:
            typ = schema.get("type")
            if isinstance(typ, str) and typ != "null":
                schema["type"] = [typ, "null"]
            elif isinstance(typ, list) and "null" not in typ:
                schema["type"] = typ + ["null"]
            enum = schema.get("enum")
            if isinstance(enum, list) and None not in enum:
                schema["enum"] = enum + [None]

        props = schema.get("properties")
        if isinstance(props, dict):
            original_required = schema.get("required", [])
            required_set = set(original_required) if isinstance(original_required, list) else set()
            schema["additionalProperties"] = False
            schema["required"] = sorted(props)
            for name, child in props.items():
                props[name] = prepare(child, name in required_set)

        for key in ("items", "additionalProperties", "not"):
            child = schema.get(key)
            if isinstance(child, dict):
                schema[key] = prepare(child)
        for key in ("allOf", "anyOf", "oneOf"):
            children = schema.get(key)
            if isinstance(children, list):
                schema[key] = [prepare(child) for child in children]
        return schema

    return {name: prepare(schema) for name, schema in resolved.items()}