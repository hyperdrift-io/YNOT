import copy

def transform(payload):
    components = payload.get("components", {}).get("schemas", {})
    prepared = {}

    def resolve(value):
        if isinstance(value, list):
            return [resolve(item) for item in value]
        if isinstance(value, dict):
            ref = value.get("$ref")
            if isinstance(ref, str) and ref.startswith("#/components/schemas/"):
                name = ref[len("#/components/schemas/"):]
                return resolve(copy.deepcopy(components[name]))
            return {key: resolve(item) for key, item in value.items()}
        return copy.deepcopy(value)

    def walk(schema, original_required):
        if isinstance(schema, list):
            return [walk(item, original_required) for item in schema]
        if not isinstance(schema, dict):
            return schema

        # Capture required before strict processing changes it.
        required_here = schema.get("required", [])
        if not isinstance(required_here, list):
            required_here = []

        result = {}
        for key, value in schema.items():
            if key == "nullable":
                continue
            if key == "default":
                continue
            if key == "$ref":
                # References have already been expanded.
                continue
            if key == "type" and schema.get("nullable") is True and isinstance(value, str):
                result[key] = [value, "null"]
            elif key in ("properties",) and isinstance(value, dict):
                result[key] = {
                    name: walk(child, name in required_here)
                    for name, child in value.items()
                }
            elif key in ("items", "not") and isinstance(value, (dict, list)):
                result[key] = walk(value, original_required)
            elif key == "additionalProperties" and isinstance(value, dict):
                result[key] = walk(value, original_required)
            elif key in ("allOf", "anyOf", "oneOf") and isinstance(value, list):
                result[key] = [walk(child, original_required) for child in value]
            else:
                result[key] = copy.deepcopy(value)

        if "properties" in schema and isinstance(schema["properties"], dict):
            result["additionalProperties"] = False
            result["required"] = sorted(schema["properties"].keys())

        if original_required is False:
            typ = result.get("type")
            if isinstance(typ, str) and typ != "null":
                result["type"] = [typ, "null"]
            elif isinstance(typ, list) and "null" not in typ:
                result["type"] = typ + ["null"]
            enum = result.get("enum")
            if isinstance(enum, list) and None not in enum:
                result["enum"] = enum + [None]

        return result

    for name, component in components.items():
        resolved = resolve(copy.deepcopy(component))
        prepared[name] = walk(resolved, True)
    return prepared