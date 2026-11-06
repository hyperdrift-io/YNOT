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

        for keyword in ('items', 'additionalItems', 'additionalProperties', 'not'):
            if keyword in schema:
                value = schema[keyword]
                if keyword == 'items' and isinstance(value, list):
                    result[keyword] = [migrate(member) for member in value]
                elif isinstance(value, dict):
                    result[keyword] = migrate(value)

        for keyword in ('allOf', 'anyOf', 'oneOf'):
            if isinstance(schema.get(keyword), list):
                result[keyword] = [migrate(member) for member in schema[keyword]]

        if 'id' in result:
            result['$id'] = result.pop('id')
        if 'definitions' in result:
            result['$defs'] = result.pop('definitions')

        reference = result.get('$ref')
        if isinstance(reference, str) and reference.startswith('#/definitions/'):
            result['$ref'] = '#/$defs/' + reference[len('#/definitions/'):]

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

        if isinstance(schema.get('items'), list):
            result['prefixItems'] = result.pop('items')
            if 'additionalItems' in result:
                result['items'] = result.pop('additionalItems')
        else:
            result.pop('additionalItems', None)

        if 'dependencies' in schema:
            required = {}
            dependent_schemas = {}
            for name, value in schema['dependencies'].items():
                if isinstance(value, list):
                    required[name] = deepcopy(value)
                else:
                    dependent_schemas[name] = migrate(value)
            result.pop('dependencies', None)
            if required:
                result['dependentRequired'] = required
            if dependent_schemas:
                result['dependentSchemas'] = dependent_schemas

        return result

    result = migrate(payload)
    if isinstance(result, dict):
        result['$schema'] = 'https://json-schema.org/draft/2020-12/schema'
    return result
