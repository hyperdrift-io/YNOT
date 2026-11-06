from copy import deepcopy


def transform(payload):
    def migrate(schema):
        if not isinstance(schema, dict):
            return deepcopy(schema)

        result = deepcopy(schema)

        for keyword in ('properties', 'patternProperties', 'definitions'):
            value = schema.get(keyword)
            if isinstance(value, dict):
                result[keyword] = {
                    name: migrate(child) for name, child in value.items()
                }

        for keyword in ('items', 'additionalItems', 'additionalProperties', 'not'):
            if keyword not in schema:
                continue
            value = schema[keyword]
            if keyword == 'items' and isinstance(value, list):
                result[keyword] = [migrate(child) for child in value]
            elif isinstance(value, dict):
                result[keyword] = migrate(value)

        for keyword in ('allOf', 'anyOf', 'oneOf'):
            if isinstance(schema.get(keyword), list):
                result[keyword] = [migrate(child) for child in schema[keyword]]

        if 'id' in result:
            result['$id'] = result.pop('id')
        if 'definitions' in result:
            result['$defs'] = result.pop('definitions')

        ref = result.get('$ref')
        if isinstance(ref, str) and ref.startswith('#/definitions/'):
            result['$ref'] = '#/$defs/' + ref[len('#/definitions/'):]

        for exclusive, inclusive in (
            ('exclusiveMinimum', 'minimum'),
            ('exclusiveMaximum', 'maximum'),
        ):
            value = result.get(exclusive)
            if value is True:
                if inclusive in result:
                    result[exclusive] = result.pop(inclusive)
                else:
                    result.pop(exclusive)
            elif value is False:
                result.pop(exclusive)

        if isinstance(schema.get('items'), list):
            result['prefixItems'] = result.pop('items')
            if 'additionalItems' in result:
                result['items'] = result.pop('additionalItems')
        else:
            result.pop('additionalItems', None)

        if 'dependencies' in schema:
            dependencies = schema['dependencies']
            required = {}
            dependent = {}
            for name, value in dependencies.items():
                if isinstance(value, list):
                    required[name] = deepcopy(value)
                else:
                    dependent[name] = migrate(value)
            result.pop('dependencies')
            if required:
                existing = result.get('dependentRequired', {})
                result['dependentRequired'] = {**existing, **required}
            if dependent:
                existing = result.get('dependentSchemas', {})
                result['dependentSchemas'] = {**existing, **dependent}

        return result

    result = migrate(payload)
    result['$schema'] = 'https://json-schema.org/draft/2020-12/schema'
    return result
