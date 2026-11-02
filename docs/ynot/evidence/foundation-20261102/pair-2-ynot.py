from copy import deepcopy


def transform(payload):
    """Convert OpenAPI 3.0 schema nullability without changing other data."""
    result = deepcopy(payload)

    def visit(schema):
        nullable = schema.pop('nullable', False)
        if nullable is True and 'type' in schema:
            schema['type'] = [schema['type'], 'null']

        if 'properties' in schema:
            for child in schema['properties'].values():
                visit(child)

        for keyword in ('items', 'additionalProperties', 'not'):
            child = schema.get(keyword)
            if isinstance(child, dict):
                visit(child)

        for keyword in ('allOf', 'anyOf', 'oneOf'):
            for child in schema.get(keyword, []):
                visit(child)

    visit(result)
    return result
