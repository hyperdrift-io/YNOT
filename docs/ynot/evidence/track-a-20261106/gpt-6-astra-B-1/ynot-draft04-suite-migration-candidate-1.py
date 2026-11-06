from copy import deepcopy


def transform(payload):
    def migrate(schema):
        if not isinstance(schema, dict):
            return deepcopy(schema)

        result = deepcopy(schema)

        for keyword in ('properties', 'patternProperties', 'definitions'):
            value = schema.get(keyword)
            if isinstance(value, dict):
                result[keyword] = {name: migrate(child) for name, child in value.items()}

        for keyword in ('additionalItems', 'additionalProperties', 'not'):
            if isinstance(schema.get(keyword), dict):
                result[keyword] = migrate(schema[keyword])

        for keyword in ('allOf', 'anyOf', 'oneOf'):
            if isinstance(schema.get(keyword), list):
                result[keyword] = [migrate(child) for child in schema[keyword]]

        if 'id' in schema:
            result['$id'] = result.pop('id')
        if 'definitions' in schema:
            result['$defs'] = result.pop('definitions')

        ref = schema.get('$ref')
        if isinstance(ref, str) and ref.startswith('#/definitions/'):
            result['$ref'] = '#/$defs/' + ref[len('#/definitions/'):]

        for exclusive, inclusive in (
            ('exclusiveMinimum', 'minimum'),
            ('exclusiveMaximum', 'maximum'),
        ):
            value = schema.get(exclusive)
            if value is True:
                if inclusive in schema:
                    result[exclusive] = result.pop(inclusive)
                else:
                    result.pop(exclusive, None)
            elif value is False:
                result.pop(exclusive, None)

        if isinstance(schema.get('items'), list):
            result['prefixItems'] = [migrate(child) for child in schema['items']]
            result.pop('items', None)
            if 'additionalItems' in schema:
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
            result.pop('dependencies')
            if required:
                result['dependentRequired'] = required
            if dependent:
                result['dependentSchemas'] = dependent

        return result

    result = migrate(payload)
    result['$schema'] = 'https://json-schema.org/draft/2020-12/schema'
    return result
