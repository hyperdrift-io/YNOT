from copy import deepcopy


def transform(payload):
    result = deepcopy(payload)

    def migrate(schema):
        if not isinstance(schema, dict):
            return schema

        if 'id' in schema:
            schema['$id'] = schema.pop('id')

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

        for keyword in ('properties', 'patternProperties', 'definitions'):
            mapping = schema.get(keyword)
            if isinstance(mapping, dict):
                for child in mapping.values():
                    migrate(child)
        if 'definitions' in schema:
            schema['$defs'] = schema.pop('definitions')

        for keyword in ('additionalProperties', 'not'):
            if keyword in schema:
                migrate(schema[keyword])

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
                schema['items'] = migrate(schema.pop('additionalItems'))
        else:
            if 'items' in schema:
                migrate(items)
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

        return schema

    migrate(result)
    if isinstance(result, dict):
        result['$schema'] = 'https://json-schema.org/draft/2020-12/schema'
    return result
