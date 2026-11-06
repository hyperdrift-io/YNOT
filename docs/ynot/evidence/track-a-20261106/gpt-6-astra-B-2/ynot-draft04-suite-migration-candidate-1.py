from copy import deepcopy


def transform(payload):
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
            dependent = {}
            for name, value in dependencies.items():
                if isinstance(value, list) and all(isinstance(v, str) for v in value):
                    required[name] = value
                else:
                    dependent[name] = migrate(value)
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

        return schema

    migrate(result)
    result['$schema'] = 'https://json-schema.org/draft/2020-12/schema'
    return result
