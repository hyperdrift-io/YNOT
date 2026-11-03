from copy import deepcopy


def transform(payload):
    """Return a migrated copy, visiting schema locations only."""
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

        for keyword in ('allOf', 'anyOf', 'oneOf'):
            children = schema.get(keyword)
            if isinstance(children, list):
                for child in children:
                    migrate(child)

        items = schema.get('items')
        if isinstance(items, list):
            for child in items:
                migrate(child)
            schema['prefixItems'] = schema.pop('items')
            if 'additionalItems' in schema:
                schema['items'] = schema.pop('additionalItems')
        else:
            migrate(items)
            schema.pop('additionalItems', None)

        if 'dependencies' in schema:
            dependencies = schema.pop('dependencies')
            required = {}
            dependent_schemas = {}
            for name, dependency in dependencies.items():
                if isinstance(dependency, list) and all(
                    isinstance(value, str) for value in dependency
                ):
                    required[name] = dependency
                else:
                    dependent_schemas[name] = migrate(dependency)
            if required:
                schema.setdefault('dependentRequired', {}).update(required)
            if dependent_schemas:
                schema.setdefault('dependentSchemas', {}).update(dependent_schemas)

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

        if 'id' in schema:
            schema['$id'] = schema.pop('id')
        if 'definitions' in schema:
            schema['$defs'] = schema.pop('definitions')

        reference = schema.get('$ref')
        if isinstance(reference, str) and reference.startswith('#/definitions/'):
            schema['$ref'] = '#/$defs/' + reference[len('#/definitions/'):]

        return schema

    migrate(result)
    if isinstance(result, dict):
        result['$schema'] = 'https://json-schema.org/draft/2020-12/schema'
    return result
