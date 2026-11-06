from copy import deepcopy


def transform(payload):
    components = payload.get("components", {}).get("schemas", {})

    def children(schema, visit):
        properties = schema.get("properties")
        if isinstance(properties, dict):
            for name, child in properties.items():
                properties[name] = visit(child)

        for key in ("items", "additionalProperties", "not"):
            if isinstance(schema.get(key), dict):
                schema[key] = visit(schema[key])

        for key in ("allOf", "anyOf", "oneOf"):
            if isinstance(schema.get(key), list):
                schema[key] = [visit(child) for child in schema[key]]
        return schema

    def resolve(schema):
        if not isinstance(schema, dict):
            return schema
        ref = schema.get("$ref")
        prefix = "#/components/schemas/"
        if isinstance(ref, str) and ref.startswith(prefix):
            name = ref[len(prefix):].replace("~1", "/").replace("~0", "~")
            return resolve(deepcopy(components[name]))
        return children(schema, resolve)

    def nullable(schema):
        if not isinstance(schema, dict):
            return schema
        flag = schema.pop("nullable", None)
        if flag is True and isinstance(schema.get("type"), str):
            kind = schema["type"]
            schema["type"] = [kind, "null"] if kind != "null" else ["null"]
        return children(schema, nullable)

    def allow_null(schema):
        if not isinstance(schema, dict):
            return
        kind = schema.get("type")
        if isinstance(kind, str) and kind != "null":
            schema["type"] = [kind, "null"]
        elif isinstance(kind, list) and "null" not in kind:
            schema["type"] = kind + ["null"]
        values = schema.get("enum")
        if isinstance(values, list) and not any(v is None for v in values):
            schema["enum"] = values + [None]

    def strict(schema):
        if not isinstance(schema, dict):
            return schema
        original_required = schema.get("required", [])
        schema.pop("default", None)
        children(schema, strict)
        if "properties" in schema:
            properties = schema["properties"]
            for name, child in properties.items():
                if name not in original_required:
                    allow_null(child)
            schema["additionalProperties"] = False
            schema["required"] = sorted(properties)
        return schema

    return {
        name: strict(nullable(resolve(deepcopy(schema))))
        for name, schema in components.items()
    }