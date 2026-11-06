from copy import deepcopy


def transform(payload):
    result = deepcopy(payload)

    def migrate(schema):
        if not isinstance(schema, dict):
            return schema

        for keyword in ('properties', 'patternProperties', 'definitions'):
            mapping = schema.get(keyword)
            if isinstance(mapping, dict):
                for key in mapping:
                    mapping[key] = migrate(mapping[key])

        for keyword in ('items', 'additionalItems', 'additionalProperties', 'not'):
            value = schema.get(keyword)
            if isinstance(value, dict):
                schema[keyword] = migrate(value)
            elif keyword == 'items' and isinstance(value, list):
                schema[keyword] = [migrate(item) for item in value]

        for keyword in ('allOf', 'anyOf', 'oneOf'):
            value = schema.get(keyword)
            if isinstance(value, list):
                schema[keyword] = [migrate(item) for item in value]

        if 'dependencies' in schema:
            dependencies = schema.pop('dependencies')
            required = {}
            dependent = {}
            for key, value in dependencies.items():
                if isinstance(value, list) and all(isinstance(item, str) for item in value):
                    required[key] = value
                else:
                    dependent[key] = migrate(value)
            if required:
                schema['dependentRequired'] = required
            if dependent:
                schema['dependentSchemas'] = dependent

        for old, new in (('id', '$id'), ('definitions', '$defs')):
            if old in schema:
                schema[new] = schema.pop(old)

        ref = schema.get('$ref')
        if isinstance(ref, str) and ref.startswith('#/definitions/'):
            schema['$ref'] = '#/$defs/' + ref[len('#/definitions/'):]

        for exclusive, inclusive in (('exclusiveMinimum', 'minimum'),
                                     ('exclusiveMaximum', 'maximum')):
            value = schema.get(exclusive)
            if value is True:
                if inclusive in schema:
                    schema[exclusive] = schema.pop(inclusive)
                else:
                    schema.pop(exclusive)
            elif value is False:
                schema.pop(exclusive)

        if isinstance(schema.get('items'), list):
            schema['prefixItems'] = schema.pop('items')
            if 'additionalItems' in schema:
                schema['items'] = schema.pop('additionalItems')
        else:
            schema.pop('additionalItems', None)

        return schema

    result = migrate(result)
    if isinstance(result, dict):
        result['$schema'] = 'https://json-schema.org/draft/2020-12/schema'
    return result
