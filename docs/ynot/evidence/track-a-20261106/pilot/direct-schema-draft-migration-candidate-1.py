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

        dependencies = schema.get('dependencies')
        if isinstance(dependencies, dict):
            for child in dependencies.values():
                if isinstance(child, dict):
                    migrate(child)

        items = schema.get('items')
        if isinstance(items, list):
            for child in items:
                migrate(child)
        elif isinstance(items, dict):
            migrate(items)

        for keyword in ('additionalItems', 'additionalProperties', 'not'):
            child = schema.get(keyword)
            if isinstance(child, dict):
                migrate(child)

        for keyword in ('allOf', 'anyOf', 'oneOf'):
            children = schema.get(keyword)
            if isinstance(children, list):
                for child in children:
                    migrate(child)

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
            if exclusive in schema:
                value = schema[exclusive]
                if value is True:
                    if inclusive in schema:
                        schema[exclusive] = schema.pop(inclusive)
                    else:
                        del schema[exclusive]
                elif value is False:
                    del schema[exclusive]

        if isinstance(items, list):
            schema['prefixItems'] = schema.pop('items')
            if 'additionalItems' in schema:
                schema['items'] = schema.pop('additionalItems')
        else:
            schema.pop('additionalItems', None)

        if isinstance(dependencies, dict):
            required = {}
            dependent_schemas = {}
            for name, value in dependencies.items():
                if isinstance(value, list) and all(isinstance(v, str) for v in value):
                    required[name] = value
                else:
                    dependent_schemas[name] = value
            del schema['dependencies']
            if required:
                schema.setdefault('dependentRequired', {}).update(required)
            if dependent_schemas:
                schema.setdefault('dependentSchemas', {}).update(dependent_schemas)

        return schema

    migrate(result)
    result['$schema'] = 'https://json-schema.org/draft/2020-12/schema'
    return result
