from copy import deepcopy


def transform(payload):
    def migrate(schema):
        if not isinstance(schema, dict):
            return deepcopy(schema)

        result = deepcopy(schema)

        for keyword in ('properties', 'patternProperties', 'definitions'):
            if isinstance(schema.get(keyword), dict):
                result[keyword] = {
                    name: migrate(value)
                    for name, value in schema[keyword].items()
                }

        for keyword in ('additionalItems', 'additionalProperties', 'not'):
            if isinstance(schema.get(keyword), dict):
                result[keyword] = migrate(schema[keyword])

        for keyword in ('allOf', 'anyOf', 'oneOf'):
            if isinstance(schema.get(keyword), list):
                result[keyword] = [migrate(value) for value in schema[keyword]]

        if isinstance(schema.get('items'), list):
            result['prefixItems'] = [migrate(value) for value in schema['items']]
            del result['items']
            if 'additionalItems' in result:
                result['items'] = result.pop('additionalItems')
        else:
            if isinstance(schema.get('items'), dict):
                result['items'] = migrate(schema['items'])
            result.pop('additionalItems', None)

        if 'dependencies' in schema:
            required = {}
            dependent = {}
            for name, value in schema['dependencies'].items():
                if isinstance(value, list) and all(isinstance(item, str) for item in value):
                    required[name] = deepcopy(value)
                else:
                    dependent[name] = migrate(value)
            del result['dependencies']
            if required:
                result['dependentRequired'] = required
            if dependent:
                result['dependentSchemas'] = dependent

        for exclusive, inclusive in (
            ('exclusiveMinimum', 'minimum'),
            ('exclusiveMaximum', 'maximum'),
        ):
            if exclusive in result:
                value = result[exclusive]
                if value is True:
                    if inclusive in result:
                        result[exclusive] = result.pop(inclusive)
                    else:
                        del result[exclusive]
                elif value is False:
                    del result[exclusive]

        if 'id' in result:
            result['$id'] = result.pop('id')
        if 'definitions' in result:
            result['$defs'] = result.pop('definitions')
        ref = result.get('$ref')
        if isinstance(ref, str) and ref.startswith('#/definitions/'):
            result['$ref'] = '#/$defs/' + ref[len('#/definitions/'):]

        return result

    result = migrate(payload)
    if isinstance(result, dict):
        result['$schema'] = 'https://json-schema.org/draft/2020-12/schema'
    return result
