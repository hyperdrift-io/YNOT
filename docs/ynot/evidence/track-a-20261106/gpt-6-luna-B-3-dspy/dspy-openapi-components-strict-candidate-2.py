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
                if key == "properties" and isinstance(value, dict):
                    result[key] = {name: resolve(child) for name, child in value.items()}
                elif key in ("items", "additionalProperties", "not"):
                    result[key] = resolve(value) if isinstance(value, dict) else copy.deepcopy(value)
                elif key in ("allOf", "anyOf", "oneOf") and isinstance(value, list):
                    result[key] = [resolve(child) for child in value]
                else:
                    result[key] = copy.deepcopy(value)
            return result
        if isinstance(schema, list):
            return [resolve(item) for item in schema]
        return copy.deepcopy(schema)

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

    def strictify(schema, original_required=None):
        if not isinstance(schema, dict):
            return

        properties = schema.get("properties")
        if isinstance(properties, dict):
            required = original_required
            if required is None:
                required = schema.get("required", [])
            required_set = set(required) if isinstance(required, list) else set()
            schema["additionalProperties"] = False
            schema["required"] = sorted(properties)
            for name, prop in properties.items():
                if name not in required_set:
                    make_nullable(prop)
                strictify(prop)

        for key in ("items", "additionalProperties", "not"):
            child = schema.get(key)
            if isinstance(child, dict):
                strictify(child)

        for key in ("allOf", "anyOf", "oneOf"):
            children = schema.get(key)
            if isinstance(children, list):
                for child in children:
                    strictify(child)

        schema.pop("default", None)

    for name, component in components.items():
        resolved = resolve(component)
        strictify(resolved)
        prepared[name] = resolved

    return prepared