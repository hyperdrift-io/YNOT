from copy import deepcopy


def transform(payload):
    def migrate(schema):
        if not isinstance(schema, dict):
            return deepcopy(schema)

        result = deepcopy(schema)

        if 'id' in schema:
            result['$id'] = result.pop('id')

        ref = schema.get('$ref')
        if isinstance(ref, str) and ref.startswith('#/definitions/'):
            result['$ref'] = '#/$defs/' + ref[len('#/definitions/'):]

        for keyword in ('properties', 'patternProperties', 'definitions'):
            if keyword in schema and isinstance(schema[keyword], dict):
                migrated = {name: migrate(value)
                            for name, value in schema[keyword].items()}
                if keyword == 'definitions':
                    result.pop('definitions')
                    result['$defs'] = migrated
                else:
                    result[keyword] = migrated

        for exclusive, inclusive in (
            ('exclusiveMinimum', 'minimum'),
            ('exclusiveMaximum', 'maximum'),
        ):
            value = schema.get(exclusive)
            if value is True:
                if inclusive in schema:
                    result[exclusive] = deepcopy(schema[inclusive])
                    result.pop(inclusive)
                else:
                    result.pop(exclusive, None)
            elif value is False:
                result.pop(exclusive, None)

        if isinstance(schema.get('items'), list):
            result.pop('items')
            result['prefixItems'] = [migrate(item) for item in schema['items']]
            if 'additionalItems' in schema:
                result['items'] = migrate(schema['additionalItems'])
        elif 'items' in schema:
            result['items'] = migrate(schema['items'])
        result.pop('additionalItems', None)

        if isinstance(schema.get('additionalProperties'), dict):
            result['additionalProperties'] = migrate(schema['additionalProperties'])
        if 'not' in schema:
            result['not'] = migrate(schema['not'])

        for keyword in ('allOf', 'anyOf', 'oneOf'):
            if isinstance(schema.get(keyword), list):
                result[keyword] = [migrate(item) for item in schema[keyword]]

        if 'dependencies' in schema:
            required = {}
            dependent = {}
            for name, value in schema['dependencies'].items():
                if isinstance(value, list) and all(isinstance(v, str) for v in value):
                    required[name] = deepcopy(value)
                else:
                    dependent[name] = migrate(value)
            result.pop('dependencies')
            for keyword, entries in (
                ('dependentRequired', required),
                ('dependentSchemas', dependent),
            ):
                if entries:
                    if isinstance(result.get(keyword), dict):
                        result[keyword].update(entries)
                    else:
                        result[keyword] = entries

        return result

    result = migrate(payload)
    if isinstance(result, dict):
        result['$schema'] = 'https://json-schema.org/draft/2020-12/schema'
    return result
