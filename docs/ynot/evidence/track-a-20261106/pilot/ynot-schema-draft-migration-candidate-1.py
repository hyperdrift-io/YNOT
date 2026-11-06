from copy import deepcopy


def transform(payload):
    """Return a migrated copy, visiting only draft-04 schema locations."""
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
                for name, child in mapping.items():
                    mapping[name] = migrate(child)
        if 'definitions' in schema:
            schema['$defs'] = schema.pop('definitions')

        for keyword in ('additionalItems', 'additionalProperties', 'not'):
            if isinstance(schema.get(keyword), dict):
                schema[keyword] = migrate(schema[keyword])

        items = schema.get('items')
        if isinstance(items, list):
            schema['prefixItems'] = [migrate(child) for child in items]
            del schema['items']
            if 'additionalItems' in schema:
                schema['items'] = schema.pop('additionalItems')
        else:
            if isinstance(items, dict):
                schema['items'] = migrate(items)
            schema.pop('additionalItems', None)

        for keyword in ('allOf', 'anyOf', 'oneOf'):
            children = schema.get(keyword)
            if isinstance(children, list):
                schema[keyword] = [migrate(child) for child in children]

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
                existing = schema.get('dependentRequired')
                schema['dependentRequired'] = {
                    **(existing if isinstance(existing, dict) else {}),
                    **required,
                }
            if dependent_schemas:
                existing = schema.get('dependentSchemas')
                schema['dependentSchemas'] = {
                    **(existing if isinstance(existing, dict) else {}),
                    **dependent_schemas,
                }

        return schema

    result = migrate(deepcopy(payload))
    result['$schema'] = 'https://json-schema.org/draft/2020-12/schema'
    return result
