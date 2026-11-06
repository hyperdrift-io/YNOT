import copy

def transform(payload):
    components = payload.get("components", {}).get("schemas", {})
    schema_keys = {"items", "not", "additionalProperties", "allOf", "anyOf", "oneOf"}

    def resolve(schema):
        if isinstance(schema, dict):
            ref = schema.get("$ref")
            if isinstance(ref, str) and ref.startswith("#/components/schemas/"):
                name = ref[len("#/components/schemas/"):]
                return resolve(copy.deepcopy(components[name]))
            result = {}
            for key, value in schema.items():
                if key == "properties" and isinstance(value, dict):
                    result[key] = {name: resolve(child) for name, child in value.items()}
                elif key in schema_keys:
                    if key == "additionalProperties":
                        result[key] = resolve(value) if isinstance(value, dict) else copy.deepcopy(value)
                    elif key in ("allOf", "anyOf", "oneOf") and isinstance(value, list):
                        result[key] = [resolve(child) for child in value]
                    else:
                        result[key] = resolve(value)
                else:
                    result[key] = copy.deepcopy(value)
            return result
        return copy.deepcopy(schema)

    def prepare(schema):
        if not isinstance(schema, dict):
            return

        nullable = schema.pop("nullable", None)
        typ = schema.get("type")
        if nullable is True and isinstance(typ, str):
            schema["type"] = [typ, "null"]

        original_required = schema.get("required", [])
        properties = schema.get("properties")

        if isinstance(properties, dict):
            for child in properties.values():
                prepare(child)
        for key in ("items", "not"):
            if key in schema:
                prepare(schema[key])
        if isinstance(schema.get("additionalProperties"), dict):
            prepare(schema["additionalProperties"])
        for key in ("allOf", "anyOf", "oneOf"):
            value = schema.get(key)
            if isinstance(value, list):
                for child in value:
                    prepare(child)

        if isinstance(properties, dict):
            names = sorted(properties)
            schema["additionalProperties"] = False
            schema["required"] = names
            for name, child in properties.items():
                if name in original_required or not isinstance(child, dict):
                    continue
                child_type = child.get("type")
                if isinstance(child_type, str) and child_type != "null":
                    child["type"] = [child_type, "null"]
                elif isinstance(child_type, list) and "null" not in child_type:
                    child["type"] = child_type + ["null"]
                enum = child.get("enum")
                if isinstance(enum, list) and None not in enum:
                    child["enum"] = enum + [None]

        schema.pop("default", None)

    result = {}
    for name, schema in components.items():
        prepared = resolve(copy.deepcopy(schema))
        prepare(prepared)
        result[name] = prepared
    return result