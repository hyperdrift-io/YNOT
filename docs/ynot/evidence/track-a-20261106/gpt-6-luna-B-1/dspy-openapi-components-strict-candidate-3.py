import copy

def transform(payload):
    components = payload.get("components", {}).get("schemas", {})
    ref_prefix = "#/components/schemas/"
    map_keys = ("properties",)
    single_keys = ("items", "additionalProperties", "not")
    list_keys = ("allOf", "anyOf", "oneOf")

    def resolve(node):
        if isinstance(node, list):
            return [resolve(item) for item in node]
        if not isinstance(node, dict):
            return copy.deepcopy(node)

        ref = node.get("$ref")
        if isinstance(ref, str) and ref.startswith(ref_prefix):
            name = ref[len(ref_prefix):]
            if name in components:
                return resolve(copy.deepcopy(components[name]))

        result = {}
        for key, value in node.items():
            if key in map_keys and isinstance(value, dict):
                result[key] = {name: resolve(child) for name, child in value.items()}
            elif key in single_keys and isinstance(value, dict):
                result[key] = resolve(value)
            elif key in list_keys and isinstance(value, list):
                result[key] = [resolve(child) for child in value]
            else:
                result[key] = copy.deepcopy(value)
        return result

    def children(schema):
        props = schema.get("properties")
        if isinstance(props, dict):
            yield from props.values()
        for key in single_keys:
            child = schema.get(key)
            if isinstance(child, dict):
                yield child
        for key in list_keys:
            value = schema.get(key)
            if isinstance(value, list):
                yield from value

    def walk(schema, visit):
        if isinstance(schema, dict):
            visit(schema)
            for child in children(schema):
                walk(child, visit)

    prepared = {}
    for name, component in components.items():
        root = resolve(component)
        original_required = {}

        def snapshot(schema):
            if "properties" in schema:
                original_required[id(schema)] = set(schema.get("required", []))

        walk(root, snapshot)

        def make_nullable(schema):
            if schema.get("nullable") is True and isinstance(schema.get("type"), str):
                schema["type"] = [schema["type"], "null"]
            schema.pop("nullable", None)

        walk(root, make_nullable)

        def make_strict(schema):
            schema.pop("default", None)
            props = schema.get("properties")
            if isinstance(props, dict):
                was_required = original_required.get(id(schema), set())
                schema["additionalProperties"] = False
                schema["required"] = sorted(props)
                for prop_name, child in props.items():
                    if prop_name not in was_required and isinstance(child, dict):
                        typ = child.get("type")
                        if isinstance(typ, str) and typ != "null":
                            child["type"] = [typ, "null"]
                        elif isinstance(typ, list) and "null" not in typ:
                            child["type"] = typ + ["null"]
                        enum = child.get("enum")
                        if isinstance(enum, list) and None not in enum:
                            child["enum"] = enum + [None]

        walk(root, make_strict)
        prepared[name] = root

    return prepared