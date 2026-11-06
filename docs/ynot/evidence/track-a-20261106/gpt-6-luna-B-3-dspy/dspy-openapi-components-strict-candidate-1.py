import copy


def transform(payload):
    components = payload.get("components", {}).get("schemas", {})
    prepared = {}

    def resolve(schema):
        if isinstance(schema, dict):
            ref = schema.get("$ref")
            if isinstance(ref, str) and ref.startswith("#/components/schemas/"):
                name = ref[len("#/components/schemas/"):]
                return resolve(copy.deepcopy(components[name]))
            result = {}
            for key, value in schema.items():
                if key == "nullable":
                    continue
                result[key] = resolve(value) if key in {
                    "properties", "items", "additionalProperties", "not",
                    "allOf", "anyOf", "oneOf"
                } else copy.deepcopy(value)
            return result
        if isinstance(schema, list):
            return [resolve(item) for item in schema]
        return copy.deepcopy(schema)

    def strictify(schema, original_required=None):
        if isinstance(schema, dict):
            properties = schema.get("properties")
            if isinstance(properties, dict):
                required_before = original_required
                if required_before is None:
                    required_before = schema.get("required", [])
                required_set = set(required_before) if isinstance(required_before, list) else set()
                schema["additionalProperties"] = False
                schema["required"] = sorted(properties)
                for name, prop in properties.items():
                    if name not in required_set and isinstance(prop, dict):
                        make_nullable(prop)
            for key in ("properties",):
                value = schema.get(key)
                if isinstance(value, dict):
                    for child in value.values():
                        strictify(child)
            for key in ("items", "additionalProperties", "not"):
                value = schema.get(key)
                if isinstance(value, dict):
                    strictify(value)
            for key in ("allOf", "anyOf", "oneOf"):
                value = schema.get(key)
                if isinstance(value, list):
                    for child in value:
                        strictify(child)
            schema.pop("default", None)

    def make_nullable(schema):
        if not isinstance(schema, dict):
            return
        typ = schema.get("type")
        if isinstance(typ, str) and typ != "null":
            schema["type"] = [typ, "null"]
        elif isinstance(typ, list) and "null" not in typ:
            schema["type"] = typ + ["null"]
        enum = schema.get("enum")
        if isinstance(enum, list) and None not in enum:
            enum.append(None)

    for name, component in components.items():
        resolved = resolve(copy.deepcopy(component))
        strictify(resolved)
        prepared[name] = resolved
    return prepared