def transform(payload):
    import copy

    document = copy.deepcopy(payload)
    document["$schema"] = "https://json-schema.org/draft/2020-12/schema"

    def visit(schema):
        if not isinstance(schema, dict):
            return schema

        if "id" in schema:
            schema["$id"] = schema.pop("id")

        if "definitions" in schema:
            schema["$defs"] = schema.pop("definitions")

        for key, value in list(schema.items()):
            if key == "$ref" and isinstance(value, str) and value.startswith("#/definitions/"):
                schema[key] = "#/$defs/" + value[len("#/definitions/"):]

        for bound, inclusive in (("exclusiveMinimum", "minimum"), ("exclusiveMaximum", "maximum")):
            if schema.get(bound) is True:
                if inclusive in schema:
                    schema[bound] = schema.pop(inclusive)
                else:
                    schema.pop(bound, None)
            elif schema.get(bound) is False:
                schema.pop(bound, None)

        items = schema.get("items")
        if isinstance(items, list):
            schema["prefixItems"] = [visit(item) for item in items]
            schema.pop("items", None)
            if "additionalItems" in schema:
                schema["items"] = visit(schema.pop("additionalItems"))
        else:
            if isinstance(items, dict):
                schema["items"] = visit(items)
            schema.pop("additionalItems", None)

        if "dependencies" in schema:
            required = {}
            dependent = {}
            for name, value in schema.pop("dependencies").items():
                if isinstance(value, list) and all(isinstance(item, str) for item in value):
                    required[name] = value
                else:
                    dependent[name] = visit(value)
            if required:
                schema["dependentRequired"] = required
            if dependent:
                schema["dependentSchemas"] = dependent

        for keyword in ("properties", "patternProperties", "$defs"):
            mapping = schema.get(keyword)
            if isinstance(mapping, dict):
                for name, child in list(mapping.items()):
                    mapping[name] = visit(child)

        for keyword in ("items", "not", "additionalItems"):
            child = schema.get(keyword)
            if isinstance(child, dict):
                schema[keyword] = visit(child)
            elif isinstance(child, list):
                schema[keyword] = [visit(item) for item in child]

        child = schema.get("additionalProperties")
        if isinstance(child, dict):
            schema["additionalProperties"] = visit(child)

        for keyword in ("allOf", "anyOf", "oneOf"):
            children = schema.get(keyword)
            if isinstance(children, list):
                schema[keyword] = [visit(item) for item in children]

        return schema

    return visit(document)
