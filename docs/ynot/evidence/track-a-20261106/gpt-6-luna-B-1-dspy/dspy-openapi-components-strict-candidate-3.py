def transform(payload):
    import copy

    components = payload.get("components", {}).get("schemas", {})
    prefix = "#/components/schemas/"

    # Stage 1: expand schema references, discarding all siblings of a $ref.
    def resolve(value):
        if isinstance(value, list):
            return [resolve(item) for item in value]
        if not isinstance(value, dict):
            return copy.deepcopy(value)

        ref = value.get("$ref")
        if isinstance(ref, str) and ref.startswith(prefix):
            name = ref[len(prefix):]
            if name not in components:
                raise KeyError(name)
            return resolve(components[name])

        result = {}
        for key, child in value.items():
            if key == "properties" and isinstance(child, dict):
                result[key] = {name: resolve(schema) for name, schema in child.items()}
            elif key in {"items", "additionalProperties", "not"} and isinstance(child, (dict, list)):
                result[key] = resolve(child)
            elif key in {"allOf", "anyOf", "oneOf"} and isinstance(child, list):
                result[key] = [resolve(schema) for schema in child]
            else:
                result[key] = copy.deepcopy(child)
        return result

    # Stage 2: convert OpenAPI nullable string types and remove nullable.
    def apply_nullability(schema):
        if isinstance(schema, list):
            return [apply_nullability(item) for item in schema]
        if not isinstance(schema, dict):
            return schema

        result = {}
        for key, value in schema.items():
            if key == "nullable":
                continue
            if key == "properties" and isinstance(value, dict):
                result[key] = {name: apply_nullability(prop) for name, prop in value.items()}
            elif key in {"items", "additionalProperties", "not"} and isinstance(value, (dict, list)):
                result[key] = apply_nullability(value)
            elif key in {"allOf", "anyOf", "oneOf"} and isinstance(value, list):
                result[key] = [apply_nullability(member) for member in value]
            else:
                result[key] = copy.deepcopy(value)

        if schema.get("nullable") is True and isinstance(schema.get("type"), str):
            result["type"] = [schema["type"], "null"]
        return result

    # Stage 3: enforce object requirements and make formerly optional fields nullable.
    def enforce_strict(schema):
        if isinstance(schema, list):
            return [enforce_strict(item) for item in schema]
        if not isinstance(schema, dict):
            return schema

        original_required = schema.get("required", [])
        properties = schema.get("properties")
        result = {}
        for key, value in schema.items():
            if key == "default":
                continue
            if key == "properties" and isinstance(value, dict):
                result[key] = {name: enforce_strict(prop) for name, prop in value.items()}
            elif key in {"items", "additionalProperties", "not"} and isinstance(value, (dict, list)):
                result[key] = enforce_strict(value)
            elif key in {"allOf", "anyOf", "oneOf"} and isinstance(value, list):
                result[key] = [enforce_strict(member) for member in value]
            else:
                result[key] = copy.deepcopy(value)

        if isinstance(properties, dict):
            names = sorted(properties)
            result["additionalProperties"] = False
            result["required"] = names
            for name in names:
                if name in original_required:
                    continue
                prop = result["properties"][name]
                if not isinstance(prop, dict):
                    continue

                typ = prop.get("type")
                if isinstance(typ, str) and typ != "null":
                    prop["type"] = [typ, "null"]
                elif isinstance(typ, list) and "null" not in typ:
                    prop["type"] = typ + ["null"]

                enum = prop.get("enum")
                if isinstance(enum, list) and None not in enum:
                    prop["enum"] = enum + [None]
        return result

    return {
        name: enforce_strict(apply_nullability(resolve(component)))
        for name, component in components.items()
    }