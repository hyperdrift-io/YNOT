import copy

def transform(payload):
    components = payload.get("components", {}).get("schemas", {})
    ref_prefix = "#/components/schemas/"

    def resolve(schema):
        if isinstance(schema, dict):
            ref = schema.get("$ref")
            if isinstance(ref, str) and ref.startswith(ref_prefix):
                name = ref[len(ref_prefix):]
                return resolve(copy.deepcopy(components[name]))

            result = {}
            for key, value in schema.items():
                if key == "properties" and isinstance(value, dict):
                    result[key] = {name: resolve(child) for name, child in value.items()}
                elif key in ("items", "not"):
                    result[key] = resolve(value)
                elif key == "additionalProperties" and isinstance(value, dict):
                    result[key] = resolve(value)
                elif key in ("allOf", "anyOf", "oneOf") and isinstance(value, list):
                    result[key] = [resolve(child) for child in value]
                else:
                    result[key] = copy.deepcopy(value)
            return result
        return copy.deepcopy(schema)

    def prepare(schema, original_required=None):
        if not isinstance(schema, dict):
            return

        nullable = schema.pop("nullable", None)
        typ = schema.get("type")
        if nullable is True and isinstance(typ, str):
            schema["type"] = [typ, "null"]

        properties = schema.get("properties")
        if isinstance(properties, dict):
            required_before = schema.get("required", [])
            for name, child in properties.items():
                prepare(child, name in required_before)

            schema["additionalProperties"] = False
            schema["required"] = sorted(properties)

            for name, child in properties.items():
                if name in required_before or not isinstance(child, dict):
                    continue
                child_type = child.get("type")
                if isinstance(child_type, str) and child_type != "null":
                    child["type"] = [child_type, "null"]
                elif isinstance(child_type, list) and "null" not in child_type:
                    child["type"] = child_type + ["null"]
                enum = child.get("enum")
                if isinstance(enum, list) and None not in enum:
                    child["enum"] = enum + [None]

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

        schema.pop("default", None)

    result = {}
    for name, schema in components.items():
        prepared = resolve(copy.deepcopy(schema))
        prepare(prepared)
        result[name] = prepared
    return result