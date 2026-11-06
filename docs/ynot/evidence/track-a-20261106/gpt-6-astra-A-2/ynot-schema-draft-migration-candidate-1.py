from copy import deepcopy


def transform(payload):
    """Return a migrated copy, visiting only draft-04 schema positions."""
    def migrate(schema):
        if not isinstance(schema, dict):
            return deepcopy(schema)

        result = deepcopy(schema)

        for keyword in ('properties', 'patternProperties', 'definitions'):
            if isinstance(schema.get(keyword), dict):
                result[keyword] = {
                    name: migrate(child)
                    for name, child in schema[keyword].items()
                }

        for keyword in ('additionalItems', 'additionalProperties', 'not'):
            if isinstance(schema.get(keyword), dict):
                result[keyword] = migrate(schema[keyword])

        for keyword in ('allOf', 'anyOf', 'oneOf'):
            if isinstance(schema.get(keyword), list):
                result[keyword] = [migrate(child) for child in schema[keyword]]

        if isinstance(schema.get('items'), list):
            result['prefixItems'] = [migrate(child) for child in schema['items']]
            del result['items']
            if 'additionalItems' in result:
                result['items'] = result.pop('additionalItems')
        else:
            if isinstance(schema.get('items'), dict):
                result['items'] = migrate(schema['items'])
            result.pop('additionalItems', None)

        if 'dependencies' in schema:
            required = {}
            dependent_schemas = {}
            for name, dependency in schema['dependencies'].items():
                if isinstance(dependency, list) and all(
                    isinstance(item, str) for item in dependency
                ):
                    required[name] = deepcopy(dependency)
                else:
                    dependent_schemas[name] = migrate(dependency)
            del result['dependencies']
            if required:
                result['dependentRequired'] = {
                    **result.get('dependentRequired', {}), **required
                }
            if dependent_schemas:
                result['dependentSchemas'] = {
                    **result.get('dependentSchemas', {}), **dependent_schemas
                }

        for exclusive, inclusive in (
            ('exclusiveMinimum', 'minimum'),
            ('exclusiveMaximum', 'maximum'),
        ):
            if result.get(exclusive) is True:
                if inclusive in result:
                    result[exclusive] = result.pop(inclusive)
                else:
                    result.pop(exclusive)
            elif result.get(exclusive) is False:
                result.pop(exclusive)

        if 'id' in result:
            result['$id'] = result.pop('id')
        if 'definitions' in result:
            result['$defs'] = result.pop('definitions')
        reference = result.get('$ref')
        if isinstance(reference, str) and reference.startswith('#/definitions/'):
            result['$ref'] = '#/$defs/' + reference[len('#/definitions/'):]

        return result

    result = migrate(payload)
    result['$schema'] = 'https://json-schema.org/draft/2020-12/schema'
    return result
