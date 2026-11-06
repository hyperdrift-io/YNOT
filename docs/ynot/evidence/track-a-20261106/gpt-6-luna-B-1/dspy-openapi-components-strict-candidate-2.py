import copy

def transform(payload):
    components = payload.get("components", {}).get("schemas", {})
    schema_maps = ("properties",)
    schema_single = ("items", "additionalProperties", "not")
    schema_lists = ("allOf", "anyOf", "oneOf")

    def resolve(node):
        if isinstance(node, list):
            return [resolve(item) for item in node]
        if not isinstance(node, dict):
            return copy.deepcopy(node)

        ref = node.get("$ref")
        prefix = "#/components/schemas/"
        if isinstance(ref, str) and ref.startswith(prefix):
            name = ref[len(prefix):]
            if name in components:
                return resolve(copy.deepcopy(components[name]))

        result = {}
        for key, value in node.items():
            if key in schema_maps and isinstance(value, dict):
                result[key] = {name: resolve(child) for name, child in value.items()}
            elif key in schema_single and isinstance(value, dict):
                result[key] = resolve(value)
            elif key in schema_lists and isinstance(value, list):
                result[key] = [resolve(child) for child in value]
            else:
                result[key] = copy.deepcopy(value)
        return result

    def walk(schema, visit):
        if not isinstance(schema, dict):
            return
        visit(schema)
        props = schema.get("properties")
        if isinstance(props, dict):
            for child in props.values():
                walk(child, visit)
        for key in schema_single:
            child = schema.get(key)
            if isinstance(child, dict):
                walk(child, visit)
        for key in schema_lists:
            children = schema.get(key)
            if isinstance(children, list):
                for child in children:
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