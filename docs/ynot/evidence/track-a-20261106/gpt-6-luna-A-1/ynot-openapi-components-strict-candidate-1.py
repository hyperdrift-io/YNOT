from copy import deepcopy


def transform(payload):
    components = payload["components"]["schemas"]
    schema_keys = {"properties", "items", "additionalProperties", "not", "allOf", "anyOf", "oneOf"}

    def prepare(schema, original_required=()):
        if isinstance(schema, list):
            return [prepare(item) for item in schema]
        if not isinstance(schema, dict):
            return schema

        ref = schema.get("$ref")
        if isinstance(ref, str) and ref.startswith("#/components/schemas/"):
            name = ref[len("#/components/schemas/"):]
            return prepare(deepcopy(components[name]))

        result = {}
        for key, value in schema.items():
            if key == "default" or key == "$ref":
                continue
            if key == "nullable":
                continue
            if key == "properties" and isinstance(value, dict):
                result[key] = {
                    prop: prepare(subschema, original_required)
                    for prop, subschema in value.items()
                }
            elif key in ("items", "not"):
                result[key] = prepare(value)
            elif key == "additionalProperties" and isinstance(value, dict):
                result[key] = prepare(value)
            elif key in ("allOf", "anyOf", "oneOf") and isinstance(value, list):
                result[key] = [prepare(member) for member in value]
            else:
                result[key] = deepcopy(value)

        typ = result.get("type")
        if schema.get("nullable") is True and isinstance(typ, str):
            result["type"] = [typ, "null"]

        props = result.get("properties")
        if isinstance(props, dict):
            required = schema.get("required", [])
            required_set = set(required) if isinstance(required, list) else set()
            for prop, subschema in props.items():
                if prop not in required_set and isinstance(subschema, dict):
                    child_type = subschema.get("type")
                    if isinstance(child_type, str) and child_type != "null":
                        subschema["type"] = [child_type, "null"]
                    elif isinstance(child_type, list) and "null" not in child_type:
                        subschema["type"] = child_type + ["null"]
                    enum = subschema.get("enum")
                    if isinstance(enum, list) and None not in enum:
                        subschema["enum"] = enum + [None]
            result["additionalProperties"] = False
            result["required"] = sorted(props)
        return result

    return {name: prepare(deepcopy(schema)) for name, schema in components.items()}
