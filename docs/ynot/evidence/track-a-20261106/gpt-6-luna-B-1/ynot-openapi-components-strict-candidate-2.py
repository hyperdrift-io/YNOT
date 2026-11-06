from copy import deepcopy


def transform(payload):
    components = payload["components"]["schemas"]

    def resolve(node):
        if isinstance(node, dict):
            ref = node.get("$ref")
            if isinstance(ref, str) and ref.startswith("#/components/schemas/"):
                name = ref[len("#/components/schemas/"):]
                return resolve(deepcopy(components[name]))

            result = {}
            for key, value in node.items():
                if key == "properties" and isinstance(value, dict):
                    result[key] = {name: resolve(child) for name, child in value.items()}
                elif key in ("items", "not", "additionalProperties") and isinstance(value, dict):
                    result[key] = resolve(value)
                elif key in ("allOf", "anyOf", "oneOf") and isinstance(value, list):
                    result[key] = [resolve(child) for child in value]
                else:
                    result[key] = deepcopy(value)
            return result
        return deepcopy(node)

    prepared = {}
    for name, component in components.items():
        schema = resolve(component)

        def walk(node):
            if not isinstance(node, dict):
                return

            if node.get("nullable") is True and isinstance(node.get("type"), str):
                node["type"] = [node["type"], "null"]
            node.pop("nullable", None)
            node.pop("default", None)

            properties = node.get("properties")
            if isinstance(properties, dict):
                original_required = node.get("required", [])
                if not isinstance(original_required, list):
                    original_required = []
                node["additionalProperties"] = False
                node["required"] = sorted(properties)

                for prop_name, prop_schema in properties.items():
                    if prop_name not in original_required and isinstance(prop_schema, dict):
                        prop_type = prop_schema.get("type")
                        if isinstance(prop_type, str) and prop_type != "null":
                            prop_schema["type"] = [prop_type, "null"]
                        elif isinstance(prop_type, list) and "null" not in prop_type:
                            prop_type.append("null")
                        enum = prop_schema.get("enum")
                        if isinstance(enum, list) and None not in enum:
                            enum.append(None)

            if isinstance(properties, dict):
                for child in properties.values():
                    walk(child)
            for key in ("items", "additionalProperties", "not"):
                child = node.get(key)
                if isinstance(child, dict):
                    walk(child)
            for key in ("allOf", "anyOf", "oneOf"):
                children = node.get(key)
                if isinstance(children, list):
                    for child in children:
                        walk(child)

        walk(schema)
        prepared[name] = schema

    return prepared