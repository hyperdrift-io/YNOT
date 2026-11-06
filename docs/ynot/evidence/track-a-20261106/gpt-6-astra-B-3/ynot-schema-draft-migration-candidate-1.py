from copy import deepcopy


def transform(payload):
    """Return a migrated copy, traversing only draft-04 schema locations."""
    def migrate(schema):
        if not isinstance(schema, dict):
            return schema

        for keyword in ('properties', 'patternProperties', 'definitions'):
            mapping = schema.get(keyword)
            if isinstance(mapping, dict):
                schema[keyword] = {
                    name: migrate(value) for name, value in mapping.items()
                }

        for keyword in ('additionalItems', 'additionalProperties', 'not'):
            if isinstance(schema.get(keyword), dict):
                schema[keyword] = migrate(schema[keyword])

        for keyword in ('allOf', 'anyOf', 'oneOf'):
            if isinstance(schema.get(keyword), list):
                schema[keyword] = [migrate(value) for value in schema[keyword]]

        items = schema.get('items')
        if isinstance(items, list):
            schema['prefixItems'] = [migrate(value) for value in items]
            del schema['items']
            if 'additionalItems' in schema:
                schema['items'] = schema.pop('additionalItems')
        else:
            if isinstance(items, dict):
                schema['items'] = migrate(items)
            schema.pop('additionalItems', None)

        if 'dependencies' in schema:
            dependencies = schema.pop('dependencies')
            required = {}
            dependent_schemas = {}
            for name, value in dependencies.items():
                if isinstance(value, list):
                    required[name] = value
                else:
                    dependent_schemas[name] = migrate(value)
            if required:
                schema.setdefault('dependentRequired', {}).update(required)
            if dependent_schemas:
                schema.setdefault('dependentSchemas', {}).update(dependent_schemas)

        for old, new in (('id', '$id'), ('definitions', '$defs')):
            if old in schema:
                schema[new] = schema.pop(old)

        ref = schema.get('$ref')
        if isinstance(ref, str) and ref.startswith('#/definitions/'):
            schema['$ref'] = '#/$defs/' + ref[len('#/definitions/'):]

        for exclusive, inclusive in (
            ('exclusiveMinimum', 'minimum'),
            ('exclusiveMaximum', 'maximum'),
        ):
            value = schema.get(exclusive)
            if value is True:
                if inclusive in schema:
                    schema[exclusive] = schema.pop(inclusive)
                else:
                    del schema[exclusive]
            elif value is False:
                del schema[exclusive]

        return schema

    result = migrate(deepcopy(payload))
    result['$schema'] = 'https://json-schema.org/draft/2020-12/schema'
    return result
