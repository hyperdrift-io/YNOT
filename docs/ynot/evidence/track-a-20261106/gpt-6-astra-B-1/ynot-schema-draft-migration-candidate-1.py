from copy import deepcopy


def transform(payload):
    def migrate(schema):
        if not isinstance(schema, dict):
            return deepcopy(schema)
        result = deepcopy(schema)

        if 'id' in result:
            result['$id'] = result.pop('id')
        ref = result.get('$ref')
        if isinstance(ref, str) and ref.startswith('#/definitions/'):
            result['$ref'] = '#/$defs/' + ref[len('#/definitions/'):]

        for keyword in ('properties', 'patternProperties', 'definitions'):
            if isinstance(schema.get(keyword), dict):
                values = {key: migrate(value) for key, value in schema[keyword].items()}
                if keyword == 'definitions':
                    result.pop('definitions', None)
                    result['$defs'] = values
                else:
                    result[keyword] = values

        for exclusive, inclusive in (('exclusiveMinimum', 'minimum'),
                                     ('exclusiveMaximum', 'maximum')):
            value = schema.get(exclusive)
            if value is True:
                if inclusive in schema:
                    result[exclusive] = deepcopy(schema[inclusive])
                    result.pop(inclusive, None)
                else:
                    result.pop(exclusive, None)
            elif value is False:
                result.pop(exclusive, None)

        if isinstance(schema.get('items'), list):
            result.pop('items', None)
            result['prefixItems'] = [migrate(item) for item in schema['items']]
            if 'additionalItems' in schema:
                result['items'] = migrate(schema['additionalItems'])
        elif 'items' in schema:
            result['items'] = migrate(schema['items'])
        result.pop('additionalItems', None)

        if 'dependencies' in schema:
            required = {}
            dependent = {}
            for key, value in schema['dependencies'].items():
                if isinstance(value, list) and all(isinstance(item, str) for item in value):
                    required[key] = deepcopy(value)
                else:
                    dependent[key] = migrate(value)
            result.pop('dependencies', None)
            if required:
                result['dependentRequired'] = required
            if dependent:
                result['dependentSchemas'] = dependent

        if isinstance(schema.get('additionalProperties'), dict):
            result['additionalProperties'] = migrate(schema['additionalProperties'])
        if 'not' in schema:
            result['not'] = migrate(schema['not'])
        for keyword in ('allOf', 'anyOf', 'oneOf'):
            if isinstance(schema.get(keyword), list):
                result[keyword] = [migrate(item) for item in schema[keyword]]
        return result

    result = migrate(payload)
    if isinstance(result, dict):
        result['$schema'] = 'https://json-schema.org/draft/2020-12/schema'
    return result
