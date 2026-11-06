from copy import deepcopy


def transform(payload):
    """Return a migrated copy, visiting only draft-04 schema positions."""
    result = deepcopy(payload)

    def migrate(schema):
        if not isinstance(schema, dict):
            return schema

        for keyword in ('properties', 'patternProperties', 'definitions'):
            mapping = schema.get(keyword)
            if isinstance(mapping, dict):
                for child in mapping.values():
                    migrate(child)

        for keyword in ('additionalItems', 'additionalProperties', 'not'):
            migrate(schema.get(keyword))

        items = schema.get('items')
        if isinstance(items, list):
            for child in items:
                migrate(child)
        else:
            migrate(items)

        for keyword in ('allOf', 'anyOf', 'oneOf'):
            children = schema.get(keyword)
            if isinstance(children, list):
                for child in children:
                    migrate(child)

        if 'dependencies' in schema:
            dependencies = schema.pop('dependencies')
            required = {}
            dependent_schemas = {}
            for name, value in dependencies.items():
                if isinstance(value, list) and all(isinstance(item, str) for item in value):
                    required[name] = value
                else:
                    dependent_schemas[name] = migrate(value)
            if required:
                schema.setdefault('dependentRequired', {}).update(required)
            if dependent_schemas:
                schema.setdefault('dependentSchemas', {}).update(dependent_schemas)

        if 'id' in schema:
            schema['$id'] = schema.pop('id')
        if 'definitions' in schema:
            schema['$defs'] = schema.pop('definitions')

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
                    schema.pop(exclusive)
            elif value is False:
                schema.pop(exclusive)

        if isinstance(items, list):
            schema['prefixItems'] = schema.pop('items')
            if 'additionalItems' in schema:
                schema['items'] = schema.pop('additionalItems')
        else:
            schema.pop('additionalItems', None)

        return schema

    migrate(result)
    result['$schema'] = 'https://json-schema.org/draft/2020-12/schema'
    return result
