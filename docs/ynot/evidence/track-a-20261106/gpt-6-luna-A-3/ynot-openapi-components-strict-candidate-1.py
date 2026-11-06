from copy import deepcopy

_SCHEMA_MAPS = ("properties",)
_SCHEMA_CHILDREN = ("items", "additionalProperties", "not")
_SCHEMA_LISTS = ("allOf", "anyOf", "oneOf")


def transform(payload):
    components = payload["components"]["schemas"]

    def resolve(schema):
        if isinstance(schema, dict):
            ref = schema.get("$ref")
            if isinstance(ref, str) and ref.startswith("#/components/schemas/"):
                name = ref[len("#/components/schemas/"):]
                return resolve(deepcopy(components[name]))
            result = {}
            for key, value in schema.items():
                if key == "properties" and isinstance(value, dict):
                    result[key] = {name: resolve(child) for name, child in value.items()}
                elif key in _SCHEMA_CHILDREN and isinstance(value, dict):
                    result[key] = resolve(value)
                elif key in _SCHEMA_LISTS and isinstance(value, list):
                    result[key] = [resolve(child) for child in value]
                else:
                    result[key] = deepcopy(value)
            return result
        return deepcopy(schema)

    def prepare(schema, originally_required):
        if isinstance(schema, dict):
            was_optional = not originally_required
            typ = schema.get("type")
            nullable = schema.get("nullable") is True
            if nullable and isinstance(typ, str):
                schema["type"] = [typ, "null"]
            schema.pop("nullable", None)

            props = schema.get("properties")
            if isinstance(props, dict):
                old_required = schema.get("required", [])
                if not isinstance(old_required, list):
                    old_required = []
                original_names = set(old_required)
                for name, child in props.items():
                    prepare(child, name in original_names)
                    if name not in original_names and isinstance(child, dict):
                        child_type = child.get("type")
                        if isinstance(child_type, str) and child_type != "null":
                            child["type"] = [child_type, "null"]
                        elif isinstance(child_type, list) and "null" not in child_type:
                            child["type"] = child_type + ["null"]
                        enum = child.get("enum")
                        if isinstance(enum, list) and None not in enum:
                            child["enum"] = enum + [None]
                schema["additionalProperties"] = False
                schema["required"] = sorted(props)

            for key in _SCHEMA_CHILDREN:
                child = schema.get(key)
                if isinstance(child, dict):
                    prepare(child, True)
            for key in _SCHEMA_LISTS:
                children = schema.get(key)
                if isinstance(children, list):
                    for child in children:
                        prepare(child, True)
            schema.pop("default", None)
        return schema

    result = {}
    for name in components:
        resolved = resolve({"$ref": "#/components/schemas/" + name})
        result[name] = prepare(resolved, True)
    return result