import copy

def transform(payload):
    components = payload.get("components", {}).get("schemas", {})
    resolved = {}

    def resolve(schema):
        if isinstance(schema, dict):
            ref = schema.get("$ref")
            if isinstance(ref, str) and ref.startswith("#/components/schemas/"):
                name = ref[len("#/components/schemas/"):]
                return resolve(copy.deepcopy(components[name]))
            result = {}
            for key, value in schema.items():
                if key in ("properties",):
                    result[key] = {name: resolve(child) for name, child in value.items()}
                elif key in ("items", "not"):
                    result[key] = resolve(value)
                elif key == "additionalProperties" and isinstance(value, dict):
                    result[key] = resolve(value)
                elif key in ("allOf", "anyOf", "oneOf"):
                    result[key] = [resolve(child) for child in value]
                else:
                    result[key] = copy.deepcopy(value)
            return result
        if isinstance(schema, list):
            return [copy.deepcopy(value) for value in schema]
        return copy.deepcopy(schema)

    def prepare(schema):
        if isinstance(schema, dict):
            nullable = schema.pop("nullable", None)
            typ = schema.get("type")
            if nullable is True and isinstance(typ, str):
                schema["type"] = [typ, "null"]

            for key, value in list(schema.items()):
                if key == "properties":
                    for child in value.values():
                        prepare(child)
                elif key in ("items", "not"):
                    prepare(value)
                elif key == "additionalProperties" and isinstance(value, dict):
                    prepare(value)
                elif key in ("allOf", "anyOf", "oneOf"):
                    for child in value:
                        prepare(child)

            if "properties" in schema:
                properties = schema["properties"]
                original_required = schema.get("required", [])
                names = sorted(properties)
                schema["additionalProperties"] = False
                schema["required"] = names
                for name, child in properties.items():
                    if name not in original_required and isinstance(child, dict):
                        child_type = child.get("type")
                        if isinstance(child_type, str) and child_type != "null":
                            child["type"] = [child_type, "null"]
                        elif isinstance(child_type, list) and "null" not in child_type:
                            child["type"] = child_type + ["null"]
                        enum = child.get("enum")
                        if isinstance(enum, list) and None not in enum:
                            child["enum"] = enum + [None]
            schema.pop("default", None)

    for name, schema in components.items():
        resolved[name] = resolve(copy.deepcopy(schema))
    for schema in resolved.values():
        prepare(schema)
    return resolved