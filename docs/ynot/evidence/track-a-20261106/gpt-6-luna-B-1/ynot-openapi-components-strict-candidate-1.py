from copy import deepcopy


def transform(payload):
    components = payload["components"]["schemas"]

    def resolve(node):
        if isinstance(node, dict):
            ref = node.get("$ref")
            if isinstance(ref, str) and ref.startswith("#/components/schemas/"):
                name = ref[len("#/components/schemas/"):]
                return resolve(deepcopy(components[name]))
            return {key: resolve(value) if _is_schema_child(key, value) else deepcopy(value)
                    for key, value in node.items()}
        if isinstance(node, list):
            return [resolve(value) for value in node]
        return deepcopy(node)

    def _is_schema_child(key, value):
        return (
            (key == "properties" and isinstance(value, dict))
            or (key in ("items", "not") and isinstance(value, dict))
            or (key == "additionalProperties" and isinstance(value, dict))
            or (key in ("allOf", "anyOf", "oneOf") and isinstance(value, list))
        )

    result = {}
    for name, component in components.items():
        resolved = resolve(component)

        def walk(schema):
            if not isinstance(schema, dict):
                return
            nullable = schema.pop("nullable", None)
            if nullable is True and isinstance(schema.get("type"), str):
                schema["type"] = [schema["type"], "null"]

            originally_required = schema.get("required", [])
            properties = schema.get("properties")
            if isinstance(properties, dict):
                schema["additionalProperties"] = False
                schema["required"] = sorted(properties)
                for prop_name, prop_schema in properties.items():
                    if prop_name not in originally_required and isinstance(prop_schema, dict):
                        prop_type = prop_schema.get("type")
                        if isinstance(prop_type, str) and prop_type != "null":
                            prop_schema["type"] = [prop_type, "null"]
                        elif isinstance(prop_type, list) and "null" not in prop_type:
                            prop_type.append("null")
                        enum = prop_schema.get("enum")
                        if isinstance(enum, list) and None not in enum:
                            enum.append(None)

            schema.pop("default", None)
            if isinstance(properties, dict):
                for child in properties.values():
                    walk(child)
            for key in ("items", "additionalProperties", "not"):
                child = schema.get(key)
                if isinstance(child, dict):
                    walk(child)
            for key in ("allOf", "anyOf", "oneOf"):
                children = schema.get(key)
                if isinstance(children, list):
                    for child in children:
                        walk(child)

        walk(resolved)
        result[name] = resolved
    return result