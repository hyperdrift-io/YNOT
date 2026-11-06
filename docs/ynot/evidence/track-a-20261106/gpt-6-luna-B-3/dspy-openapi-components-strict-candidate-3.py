import copy

def transform(payload):
    components = payload.get("components", {}).get("schemas", {})
    ref_prefix = "#/components/schemas/"
    schema_maps = {"properties"}
    schema_lists = {"allOf", "anyOf", "oneOf"}
    schema_singles = {"items", "not"}

    def visit_children(schema, visit):
        """Copy a schema, applying visit only at defined schema positions."""
        if not isinstance(schema, dict):
            return copy.deepcopy(schema)
        result = {}
        for key, value in schema.items():
            if key in schema_maps and isinstance(value, dict):
                result[key] = {name: visit(child) for name, child in value.items()}
            elif key in schema_lists and isinstance(value, list):
                result[key] = [visit(child) for child in value]
            elif key in schema_singles and isinstance(value, dict):
                result[key] = visit(value)
            elif key == "additionalProperties" and isinstance(value, dict):
                result[key] = visit(value)
            else:
                result[key] = copy.deepcopy(value)
        return result

    # Stage 1: replace references throughout schema positions, discarding siblings.
    def resolve(schema):
        if not isinstance(schema, dict):
            return copy.deepcopy(schema)
        ref = schema.get("$ref")
        if isinstance(ref, str) and ref.startswith(ref_prefix):
            name = ref[len(ref_prefix):]
            return resolve(copy.deepcopy(components[name]))
        return visit_children(schema, resolve)

    # Stage 2: apply OpenAPI nullable semantics throughout schema positions.
    def nullability(schema):
        result = visit_children(schema, nullability)
        if isinstance(schema, dict):
            result.pop("nullable", None)
            if schema.get("nullable") is True and isinstance(schema.get("type"), str):
                result["type"] = [schema["type"], "null"]
        return result

    # Stage 3: make schemas strict, using each object's original required list
    # to determine which of its properties may be null.
    def strict(schema, optional=False):
        if not isinstance(schema, dict):
            return copy.deepcopy(schema)

        original_required = schema.get("required", [])
        properties = schema.get("properties")
        result = {}
        for key, value in schema.items():
            if key == "default":
                continue
            if key == "properties" and isinstance(value, dict):
                result[key] = {
                    name: strict(child, name not in original_required)
                    for name, child in value.items()
                }
            elif key in schema_lists and isinstance(value, list):
                result[key] = [strict(child) for child in value]
            elif key in schema_singles and isinstance(value, dict):
                result[key] = strict(value)
            elif key == "additionalProperties" and isinstance(value, dict):
                result[key] = strict(value)
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
        name: strict(nullability(resolve(schema)))
        for name, schema in components.items()
    }