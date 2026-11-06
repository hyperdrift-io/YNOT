import copy

def transform(payload):
    components = payload.get("components", {}).get("schemas", {})
    result = {}

    def resolve(value):
        if isinstance(value, dict):
            ref = value.get("$ref")
            if isinstance(ref, str) and ref.startswith("#/components/schemas/"):
                name = ref[len("#/components/schemas/"):]
                return resolve(copy.deepcopy(components[name]))
            return {key: resolve(child) if is_schema_child(key, child) else copy.deepcopy(child)
                    for key, child in value.items()}
        if isinstance(value, list):
            return [resolve(item) for item in value]
        return copy.deepcopy(value)

    def is_schema_child(key, child):
        return key in ("properties", "items", "not", "allOf", "anyOf", "oneOf", "additionalProperties")

    def prepare(schema, parent_required=None, property_name=None):
        if isinstance(schema, list):
            return [prepare(item) for item in schema]
        if not isinstance(schema, dict):
            return schema

        original_required = set(schema.get("required", [])) if parent_required is None else parent_required
        out = {}
        for key, value in schema.items():
            if key in ("nullable", "default"):
                continue
            if key == "properties" and isinstance(value, dict):
                out[key] = {
                    name: prepare(child, original_required, name)
                    for name, child in value.items()
                }
            elif key in ("items", "not") and isinstance(value, dict):
                out[key] = prepare(value)
            elif key == "additionalProperties" and isinstance(value, dict):
                out[key] = prepare(value)
            elif key in ("allOf", "anyOf", "oneOf") and isinstance(value, list):
                out[key] = [prepare(child) for child in value]
            else:
                out[key] = copy.deepcopy(value)

        if schema.get("nullable") is True and isinstance(schema.get("type"), str):
            typ = schema["type"]
            if isinstance(out.get("type"), str):
                out["type"] = [typ, "null"]

        if property_name is not None and property_name not in original_required:
            typ = out.get("type")
            if isinstance(typ, str) and typ != "null":
                out["type"] = [typ, "null"]
            elif isinstance(typ, list) and "null" not in typ:
                out["type"] = typ + ["null"]
            if "enum" in out and isinstance(out["enum"], list) and None not in out["enum"]:
                out["enum"] = out["enum"] + [None]

        if "properties" in out and isinstance(out["properties"], dict):
            out["additionalProperties"] = False
            out["required"] = sorted(out["properties"])
        return out

    for name, schema in components.items():
        resolved = resolve(copy.deepcopy(schema))
        result[name] = prepare(resolved)
    return result