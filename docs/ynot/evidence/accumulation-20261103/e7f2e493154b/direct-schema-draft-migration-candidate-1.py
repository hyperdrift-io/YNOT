from copy import deepcopy


def transform(payload):
    def migrate(schema):
        if not isinstance(schema, dict):
            return schema

        for keyword in ('properties', 'patternProperties', 'definitions'):
            mapping = schema.get(keyword)
            if isinstance(mapping, dict):
                for name, child in mapping.items():
                    mapping[name] = migrate(child)

        for keyword in ('items', 'additionalItems', 'additionalProperties', 'not'):
            child = schema.get(keyword)
            if keyword == 'items' and isinstance(child, list):
                schema[keyword] = [migrate(item) for item in child]
            elif isinstance(child, dict):
                schema[keyword] = migrate(child)

        for keyword in ('allOf', 'anyOf', 'oneOf'):
            children = schema.get(keyword)
            if isinstance(children, list):
                schema[keyword] = [migrate(child) for child in children]

        if 'id' in schema:
            schema['$id'] = schema.pop('id')
        if 'definitions' in schema:
            schema['$defs'] = schema.pop('definitions')

        ref = schema.get('$ref')
        if isinstance(ref, str) and ref.startswith('#/definitions/'):
            schema['$ref'] = '#/$defs/' + ref[len('#/definitions/'):]

        for exclusive, bound in (
            ('exclusiveMinimum', 'minimum'),
            ('exclusiveMaximum', 'maximum'),
        ):
            value = schema.get(exclusive)
            if value is True:
                if bound in schema:
                    schema[exclusive] = schema.pop(bound)
                else:
                    schema.pop(exclusive)
            elif value is False:
                schema.pop(exclusive)

        if isinstance(schema.get('items'), list):
            schema['prefixItems'] = schema.pop('items')
            if 'additionalItems' in schema:
                schema['items'] = schema.pop('additionalItems')
        else:
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
                schema.setdefault('dependentRequired', {}).update(required)
            if dependent:
                schema.setdefault('dependentSchemas', {}).update(dependent)

        return schema

    result = migrate(deepcopy(payload))
    result['$schema'] = 'https://json-schema.org/draft/2020-12/schema'
    return result
