import copy

def transform(payload):
    components = payload.get("components", {}).get("schemas", {})
    names = list(components)

    def resolve(value):
        if isinstance(value, dict):
            ref = value.get("$ref")
            if isinstance(ref, str) and ref.startswith("#/components/schemas/"):
                name = ref[len("#/components/schemas/"):]
                if name in components:
                    return resolve(copy.deepcopy(components[name]))
            result = {}
            for key, item in value.items():
                if key == "nullable":
                    continue
                result[key] = resolve(item) if key in SCHEMA_MAP_KEYS else copy.deepcopy(item)
            if value.get("nullable") is True and isinstance(value.get("type"), str):
                result["type"] = [value["type"], "null"]
            return result
        if isinstance(value, list):
            return [resolve(item) for item in value]
        return copy.deepcopy(value)

    SCHEMA_MAP_KEYS = {"properties", "allOf", "anyOf", "oneOf"}
    SCHEMA_SINGLE_KEYS = {"items", "not"}
    SCHEMA_OBJECT_KEYS = {"additionalProperties"}

    def prepare(schema, parent_required=None, property_name=None):
        if isinstance(schema, list):
            return [prepare(item) for item in schema]
        if not isinstance(schema, dict):
            return schema

        original_required = schema.get("required", [])
        result = {}
        for key, value in schema.items():
            if key in ("nullable", "default"):
                continue
            if key == "properties" and isinstance(value, dict):
                result[key] = {
                    name: prepare(child, original_required, name)
                    for name, child in value.items()
                }
            elif key in ("allOf", "anyOf", "oneOf") and isinstance(value, list):
                result[key] = [prepare(child) for child in value]
            elif key in ("items", "not") and isinstance(value, (dict, list)):
                result[key] = prepare(value)
            elif key == "additionalProperties" and isinstance(value, dict):
                result[key] = prepare(value)
            else:
                result[key] = copy.deepcopy(value)

        if "properties" in schema and isinstance(schema["properties"], dict):
            properties = schema["properties"]
            result["additionalProperties"] = False
            result["required"] = sorted(properties)

        if property_name is not None and parent_required is not None and property_name not in parent_required:
            typ = result.get("type")
            if isinstance(typ, str) and typ != "null":
                result["type"] = [typ, "null"]
            elif isinstance(typ, list) and "null" not in typ:
                result["type"] = typ + ["null"]
            enum = result.get("enum")
            if isinstance(enum, list) and None not in enum:
                result["enum"] = enum + [None]

        return result

    output = {}
    for name in names:
        output[name] = prepare(resolve(copy.deepcopy(components[name])))
    return output