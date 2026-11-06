from copy import deepcopy


def transform(payload):
    """Convert OpenAPI 3.0 nullability at schema positions only.

    All other constraints and annotation data are preserved. The input
    schema is not mutated.
    """
    def convert(schema):
        result = dict(schema)
        nullable = result.pop('nullable', None)
        if nullable is True and 'type' in result:
            result['type'] = [result['type'], 'null']

        if 'properties' in result:
            result['properties'] = {
                name: convert(child)
                for name, child in result['properties'].items()
            }

        for keyword in ('items', 'additionalProperties', 'not'):
            if keyword in result and isinstance(result[keyword], dict):
                result[keyword] = convert(result[keyword])

        for keyword in ('allOf', 'anyOf', 'oneOf'):
            if keyword in result:
                result[keyword] = [convert(child) for child in result[keyword]]

        return result

    return convert(deepcopy(payload))
