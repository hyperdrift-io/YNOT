import copy


def transform(payload):
    components = payload.get("components", {}).get("schemas", {})

    def resolve(schema):
        if isinstance(schema, dict):
            ref = schema.get("$ref")
            if isinstance(ref, str) and ref.startswith("#/components/schemas/"):
                name = ref[len("#/components/schemas/"):]
                return resolve(copy.deepcopy(components[name]))

            result = {}
            for key, value in schema.items():
                if key == "properties" and isinstance(value, dict):
                    result[key] = {name: resolve(child) for name, child in value.items()}
                elif key in ("items", "not", "additionalProperties") and isinstance(value, dict):
                    result[key] = resolve(value)
                elif key in ("allOf", "anyOf", "oneOf") and isinstance(value, list):
                    result[key] = [resolve(child) for child in value]
                else:
                    result[key] = copy.deepcopy(value)
            return result
        return copy.deepcopy(schema)

    def prepare(schema, parent_required=None, is_property=False):
        if not isinstance(schema, dict):
            return copy.deepcopy(schema)

        original_required = (
            set(schema.get("required", []))
            if parent_required is None
            else parent_required
        )
        result = {}

        for key, value in schema.items():
            if key in ("nullable", "default"):
                continue
            if key == "properties" and isinstance(value, dict):
                result[key] = {
                    name: prepare(child, original_required, True)
                    for name, child in value.items()
                }
            elif key in ("items", "not", "additionalProperties") and isinstance(value, dict):
                result[key] = prepare(value)
            elif key in ("allOf", "anyOf", "oneOf") and isinstance(value, list):
                result[key] = [prepare(child) for child in value]
            else:
                result[key] = copy.deepcopy(value)

        if schema.get("nullable") is True and isinstance(schema.get("type"), str):
            result["type"] = [schema["type"], "null"]

        if is_property and parent_required is not None:
            # The property name is passed separately below through its prepared value.
            pass

        if isinstance(result.get("properties"), dict):
            result["additionalProperties"] = False
            result["required"] = sorted(result["properties"])

        return result

    def prepare_component(schema):
        def walk(current, parent_required=None, property_name=None):
            if not isinstance(current, dict):
                return copy.deepcopy(current)

            original_required = (
                set(current.get("required", []))
                if parent_required is None
                else parent_required
            )
            result = {}
            for key, value in current.items():
                if key in ("nullable", "default"):
                    continue
                if key == "properties" and isinstance(value, dict):
                    result[key] = {
                        name: walk(child, original_required, name)
                        for name, child in value.items()
                    }
                elif key in ("items", "not", "additionalProperties") and isinstance(value, dict):
                    result[key] = walk(value)
                elif key in ("allOf", "anyOf", "oneOf") and isinstance(value, list):
                    result[key] = [walk(child) for child in value]
                else:
                    result[key] = copy.deepcopy(value)

            if current.get("nullable") is True and isinstance(current.get("type"), str):
                result["type"] = [current["type"], "null"]

            if property_name is not None and property_name not in original_required:
                typ = result.get("type")
                if isinstance(typ, str) and typ != "null":
                    result["type"] = [typ, "null"]
                elif isinstance(typ, list) and "null" not in typ:
                    result["type"] = typ + ["null"]
                if isinstance(result.get("enum"), list) and None not in result["enum"]:
                    result["enum"] = result["enum"] + [None]

            if isinstance(result.get("properties"), dict):
                result["additionalProperties"] = False
                result["required"] = sorted(result["properties"])
            return result

        return walk(schema)

    return {
        name: prepare_component(resolve(copy.deepcopy(schema)))
        for name, schema in components.items()
    }