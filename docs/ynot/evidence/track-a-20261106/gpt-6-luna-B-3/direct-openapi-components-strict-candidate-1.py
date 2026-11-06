from copy import deepcopy


def transform(payload):
    components = payload.get("components", {}).get("schemas", {})
    resolving = set()

    def resolve_ref(name):
        if name in resolving:
            raise ValueError("reference cycle")
        resolving.add(name)
        try:
            return visit(deepcopy(components[name]))
        finally:
            resolving.remove(name)

    def visit(value):
        if isinstance(value, list):
            return [visit(item) for item in value]
        if not isinstance(value, dict):
            return value

        ref = value.get("$ref")
        if isinstance(ref, str) and ref.startswith("#/components/schemas/"):
            return resolve_ref(ref[len("#/components/schemas/"):])

        schema = {}
        for key, item in value.items():
            if key in ("properties", "allOf", "anyOf", "oneOf") and isinstance(item, dict):
                schema[key] = {name: visit(child) for name, child in item.items()}
            elif key in ("items", "not") and isinstance(item, dict):
                schema[key] = visit(item)
            elif key == "additionalProperties" and isinstance(item, dict):
                schema[key] = visit(item)
            elif key in ("allOf", "anyOf", "oneOf") and isinstance(item, list):
                schema[key] = [visit(child) for child in item]
            else:
                schema[key] = deepcopy(item)

        nullable = schema.pop("nullable", None)
        if nullable is True and isinstance(schema.get("type"), str):
            schema["type"] = [schema["type"], "null"]

        schema.pop("default", None)
        if isinstance(schema.get("properties"), dict):
            properties = schema["properties"]
            original_required = value.get("required", [])
            if not isinstance(original_required, list):
                original_required = []
            for name, prop in properties.items():
                if name not in original_required and isinstance(prop, dict):
                    prop_type = prop.get("type")
                    if isinstance(prop_type, str) and prop_type != "null":
                        prop["type"] = [prop_type, "null"]
                    elif isinstance(prop_type, list) and "null" not in prop_type:
                        prop["type"] = prop_type + ["null"]
                    if isinstance(prop.get("enum"), list) and None not in prop["enum"]:
                        prop["enum"] = prop["enum"] + [None]
            schema["additionalProperties"] = False
            schema["required"] = sorted(properties)
        return schema

    return {name: visit(deepcopy(schema)) for name, schema in components.items()}
