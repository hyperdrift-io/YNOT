import copy
from urllib.parse import unquote

def transform(payload):
    components = payload.get("components", {}).get("schemas", {})
    prepared = {}

    def resolve(value):
        if isinstance(value, dict):
            ref = value.get("$ref")
            if isinstance(ref, str) and ref.startswith("#/components/schemas/"):
                name = unquote(ref[len("#/components/schemas/"):]).replace("~1", "/").replace("~0", "~")
                return resolve(copy.deepcopy(components[name]))
            return {key: resolve(item) for key, item in value.items()}
        if isinstance(value, list):
            return [resolve(item) for item in value]
        return copy.deepcopy(value)

    def prepare(schema, parent_required=True):
        if isinstance(schema, list):
            return [prepare(item, parent_required) for item in schema]
        if not isinstance(schema, dict):
            return copy.deepcopy(schema)

        original_required = schema.get("required", [])
        if not isinstance(original_required, list):
            original_required = []

        result = {}
        for key, value in schema.items():
            if key in ("nullable", "default", "$ref"):
                continue
            if key == "type" and schema.get("nullable") is True and isinstance(value, str):
                result[key] = [value, "null"]
            elif key == "properties" and isinstance(value, dict):
                result[key] = {
                    name: prepare(child, name in original_required)
                    for name, child in value.items()
                }
            elif key in ("items", "not") and isinstance(value, (dict, list)):
                result[key] = prepare(value, parent_required)
            elif key == "additionalProperties" and isinstance(value, dict):
                result[key] = prepare(value, parent_required)
            elif key in ("allOf", "anyOf", "oneOf") and isinstance(value, list):
                result[key] = [prepare(child, parent_required) for child in value]
            else:
                result[key] = copy.deepcopy(value)

        if isinstance(schema.get("properties"), dict):
            result["additionalProperties"] = False
            result["required"] = sorted(schema["properties"])

        if not parent_required:
            typ = result.get("type")
            if isinstance(typ, str) and typ != "null":
                result["type"] = [typ, "null"]
            elif isinstance(typ, list) and "null" not in typ:
                result["type"] = typ + ["null"]
            enum = result.get("enum")
            if isinstance(enum, list) and None not in enum:
                result["enum"] = enum + [None]

        return result

    for name, component in components.items():
        prepared[name] = prepare(resolve(copy.deepcopy(component)), True)
    return prepared