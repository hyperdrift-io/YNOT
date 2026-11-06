import copy

def transform(payload):
    components = payload.get("components", {}).get("schemas", {})
    resolved_components = {}

    def resolve(value):
        if isinstance(value, dict):
            ref = value.get("$ref")
            if isinstance(ref, str) and ref.startswith("#/components/schemas/"):
                name = ref[len("#/components/schemas/"):]
                return resolve(copy.deepcopy(components[name]))
            out = {}
            for key, child in value.items():
                if key == "properties" and isinstance(child, dict):
                    out[key] = {name: resolve(schema) for name, schema in child.items()}
                elif key in ("items", "additionalProperties", "not") and isinstance(child, dict):
                    out[key] = resolve(child)
                elif key in ("allOf", "anyOf", "oneOf") and isinstance(child, list):
                    out[key] = [resolve(schema) for schema in child]
                else:
                    out[key] = copy.deepcopy(child)
            return out
        return copy.deepcopy(value)

    for name, schema in components.items():
        resolved_components[name] = resolve(copy.deepcopy(schema))

    def prepare(schema, required_by_parent=None, property_name=None):
        if not isinstance(schema, dict):
            return copy.deepcopy(schema)

        original_required = set(schema.get("required", [])) if required_by_parent is None else required_by_parent
        out = {}
        for key, value in schema.items():
            if key in ("nullable", "default"):
                continue
            if key == "properties" and isinstance(value, dict):
                out[key] = {
                    name: prepare(child, original_required, name)
                    for name, child in value.items()
                }
            elif key in ("items", "additionalProperties", "not") and isinstance(value, dict):
                out[key] = prepare(value)
            elif key in ("allOf", "anyOf", "oneOf") and isinstance(value, list):
                out[key] = [prepare(child) for child in value]
            else:
                out[key] = copy.deepcopy(value)

        if schema.get("nullable") is True and isinstance(schema.get("type"), str):
            out["type"] = [schema["type"], "null"]

        if property_name is not None and property_name not in original_required:
            typ = out.get("type")
            if isinstance(typ, str) and typ != "null":
                out["type"] = [typ, "null"]
            elif isinstance(typ, list) and "null" not in typ:
                out["type"] = typ + ["null"]
            if isinstance(out.get("enum"), list) and None not in out["enum"]:
                out["enum"] = out["enum"] + [None]

        if isinstance(out.get("properties"), dict):
            out["additionalProperties"] = False
            out["required"] = sorted(out["properties"])
        return out

    return {
        name: prepare(schema)
        for name, schema in resolved_components.items()
    }