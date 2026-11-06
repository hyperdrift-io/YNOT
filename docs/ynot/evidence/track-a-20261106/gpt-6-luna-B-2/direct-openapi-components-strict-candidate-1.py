from copy import deepcopy


def transform(payload):
    components = payload["components"]["schemas"]

    def resolve(value):
        if isinstance(value, list):
            return [resolve(item) for item in value]
        if not isinstance(value, dict):
            return deepcopy(value)
        ref = value.get("$ref")
        if isinstance(ref, str) and ref.startswith("#/components/schemas/"):
            name = ref[len("#/components/schemas/"):]
            return resolve(deepcopy(components[name]))
        result = {}
        for key, item in value.items():
            if key in ("properties",) and isinstance(item, dict):
                result[key] = {name: resolve(schema) for name, schema in item.items()}
            elif key in ("items", "additionalProperties", "not") and isinstance(item, dict):
                result[key] = resolve(item)
            elif key in ("allOf", "anyOf", "oneOf") and isinstance(item, list):
                result[key] = [resolve(schema) for schema in item]
            else:
                result[key] = deepcopy(item)
        return result

    def prepare(schema, originally_required=True):
        if isinstance(schema, list):
            return [prepare(item, originally_required) for item in schema]
        if not isinstance(schema, dict):
            return schema

        schema = deepcopy(schema)
        required = set(schema.get("required", [])) if isinstance(schema.get("required", []), list) else set()
        properties = schema.get("properties")
        if isinstance(properties, dict):
            prepared_properties = {}
            for name, child in properties.items():
                child = prepare(child, name in required)
                if name not in required and isinstance(child, dict):
                    typ = child.get("type")
                    if isinstance(typ, str) and typ != "null":
                        child["type"] = [typ, "null"]
                    elif isinstance(typ, list) and "null" not in typ:
                        child["type"] = typ + ["null"]
                    enum = child.get("enum")
                    if isinstance(enum, list) and None not in enum:
                        child["enum"] = enum + [None]
                prepared_properties[name] = child
            schema["properties"] = prepared_properties
            schema["additionalProperties"] = False
            schema["required"] = sorted(properties)

        def visit(key):
            value = schema.get(key)
            if isinstance(value, dict):
                schema[key] = prepare(value)
            elif isinstance(value, list):
                schema[key] = [prepare(item) for item in value]

        for key in ("items", "additionalProperties", "not"):
            visit(key)
        for key in ("allOf", "anyOf", "oneOf"):
            visit(key)

        nullable = schema.pop("nullable", None)
        typ = schema.get("type")
        if nullable is True and isinstance(typ, str):
            schema["type"] = [typ, "null"]
        schema.pop("default", None)
        return schema

    # Resolve only schema-position values, discarding siblings whenever a ref occurs.
    resolved = {name: resolve({"$ref": "#/components/schemas/" + name}) for name in components}
    return {name: prepare(schema) for name, schema in resolved.items()}