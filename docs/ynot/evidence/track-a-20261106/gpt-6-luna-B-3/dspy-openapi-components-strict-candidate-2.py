import copy

def transform(payload):
    components = payload.get("components", {}).get("schemas", {})
    ref_prefix = "#/components/schemas/"

    # Stage 1: resolve references only at schema positions.
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
                elif key in ("items", "not") and isinstance(value, dict):
                    result[key] = resolve(value)
                elif key == "additionalProperties" and isinstance(value, dict):
                    result[key] = resolve(value)
                elif key in ("allOf", "anyOf", "oneOf") and isinstance(value, list):
                    result[key] = [resolve(child) for child in value]
                else:
                    result[key] = copy.deepcopy(value)
            return result
        return copy.deepcopy(schema)

    # Stage 2: convert nullable types and remove nullable throughout schema positions.
    def apply_nullability(schema):
        if not isinstance(schema, dict):
            return schema
        result = {}
        for key, value in schema.items():
            if key == "nullable":
                continue
            if key == "properties" and isinstance(value, dict):
                result[key] = {name: apply_nullability(child) for name, child in value.items()}
            elif key in ("items", "not") and isinstance(value, dict):
                result[key] = apply_nullability(value)
            elif key == "additionalProperties" and isinstance(value, dict):
                result[key] = apply_nullability(value)
            elif key in ("allOf", "anyOf", "oneOf") and isinstance(value, list):
                result[key] = [apply_nullability(child) for child in value]
            else:
                result[key] = copy.deepcopy(value)
        if schema.get("nullable") is True and isinstance(schema.get("type"), str):
            result["type"] = [schema["type"], "null"]
        return result

    # Stage 3: enforce required properties, closed objects, optional-property nulls,
    # and remove defaults, while visiting only schema positions.
    def make_strict(schema, optional=False):
        if not isinstance(schema, dict):
            return schema
        original_required = schema.get("required", [])
        properties = schema.get("properties")
        result = {}
        for key, value in schema.items():
            if key == "default":
                continue
            if key == "properties" and isinstance(value, dict):
                result[key] = {
                    name: make_strict(child, name not in original_required)
                    for name, child in value.items()
                }
            elif key in ("items", "not") and isinstance(value, dict):
                result[key] = make_strict(value)
            elif key == "additionalProperties" and isinstance(value, dict):
                result[key] = make_strict(value)
            elif key in ("allOf", "anyOf", "oneOf") and isinstance(value, list):
                result[key] = [make_strict(child) for child in value]
            else:
                result[key] = copy.deepcopy(value)

        if isinstance(properties, dict):
            result["additionalProperties"] = False
            result["required"] = sorted(properties)

        if optional:
            typ = result.get("type")
            if isinstance(typ, str) and typ != "null":
                result["type"] = [typ, "null"]
            elif isinstance(typ, list) and "null" not in typ:
                result["type"] = typ + ["null"]
            enum = result.get("enum")
            if isinstance(enum, list) and None not in enum:
                result["enum"] = enum + [None]
        return result

    return {
        name: make_strict(apply_nullability(resolve(schema)))
        for name, schema in components.items()
    }