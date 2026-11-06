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
            child = schema.get(keyword)
            if isinstance(child, dict):
                migrate(child)

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
            if isinstance(items, dict):
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
                schema['dependentRequired'] = required
            if dependent_schemas:
                schema['dependentSchemas'] = dependent_schemas

        for bound, exclusive in (
            ('minimum', 'exclusiveMinimum'),
            ('maximum', 'exclusiveMaximum'),
        ):
            value = schema.get(exclusive)
            if value is True:
                if bound in schema:
                    schema[exclusive] = schema.pop(bound)
                else:
                    schema.pop(exclusive)
            elif value is False:
                schema.pop(exclusive)

        if 'id' in schema:
            schema['$id'] = schema.pop('id')
        if 'definitions' in schema:
            schema['$defs'] = schema.pop('definitions')
        ref = schema.get('$ref')
        if isinstance(ref, str) and ref.startswith('#/definitions/'):
            schema['$ref'] = '#/$defs/' + ref[len('#/definitions/'):]
        return schema

    migrate(result)
    result['$schema'] = 'https://json-schema.org/draft/2020-12/schema'
    return result
