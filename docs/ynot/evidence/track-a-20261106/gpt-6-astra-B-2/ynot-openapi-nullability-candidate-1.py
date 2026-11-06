from copy import deepcopy


def transform(payload):
    """Convert OpenAPI 3.0 schema nullability to OpenAPI 3.1.

    Only schema positions are traversed. Annotation data and all other
    constraints are preserved, and the input is not mutated.
    """
    result = deepcopy(payload)

    def convert(schema):
        nullable = schema.pop('nullable', False)
        if nullable is True and 'type' in schema:
            schema['type'] = [schema['type'], 'null']

        if 'properties' in schema:
            for child in schema['properties'].values():
                convert(child)

        for keyword in ('items', 'additionalProperties', 'not'):
            child = schema.get(keyword)
            if isinstance(child, dict):
                convert(child)

        for keyword in ('allOf', 'anyOf', 'oneOf'):
            for child in schema.get(keyword, []):
                convert(child)

    convert(result)
    return result
