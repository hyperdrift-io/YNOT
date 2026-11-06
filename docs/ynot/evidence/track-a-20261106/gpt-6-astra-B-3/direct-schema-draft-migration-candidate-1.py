from copy import deepcopy


def transform(payload):
    def migrate(schema):
        if not isinstance(schema, dict):
            return deepcopy(schema)

        out = deepcopy(schema)

        for keyword in ('properties', 'patternProperties', 'definitions'):
            if isinstance(schema.get(keyword), dict):
                out[keyword] = {
                    name: migrate(value)
                    for name, value in schema[keyword].items()
                }

        for keyword in ('additionalItems', 'additionalProperties', 'not'):
            if isinstance(schema.get(keyword), dict):
                out[keyword] = migrate(schema[keyword])

        for keyword in ('allOf', 'anyOf', 'oneOf'):
            if isinstance(schema.get(keyword), list):
                out[keyword] = [migrate(value) for value in schema[keyword]]

        if 'id' in out:
            out['$id'] = out.pop('id')
        if 'definitions' in out:
            out['$defs'] = out.pop('definitions')

        ref = out.get('$ref')
        if isinstance(ref, str) and ref.startswith('#/definitions/'):
            out['$ref'] = '#/$defs/' + ref[len('#/definitions/'):]

        for exclusive, inclusive in (
            ('exclusiveMinimum', 'minimum'),
            ('exclusiveMaximum', 'maximum'),
        ):
            value = out.get(exclusive)
            if value is True:
                if inclusive in out:
                    out[exclusive] = out.pop(inclusive)
                else:
                    out.pop(exclusive)
            elif value is False:
                out.pop(exclusive)

        if isinstance(schema.get('items'), list):
            out['prefixItems'] = [migrate(value) for value in schema['items']]
            out.pop('items')
            if 'additionalItems' in out:
                out['items'] = out.pop('additionalItems')
        else:
            if isinstance(schema.get('items'), dict):
                out['items'] = migrate(schema['items'])
            out.pop('additionalItems', None)

        if 'dependencies' in schema:
            required = {}
            dependent_schemas = {}
            for name, value in schema['dependencies'].items():
                if isinstance(value, list) and all(isinstance(v, str) for v in value):
                    required[name] = deepcopy(value)
                else:
                    dependent_schemas[name] = migrate(value)
            out.pop('dependencies')
            if required:
                out.setdefault('dependentRequired', {}).update(required)
            if dependent_schemas:
                out.setdefault('dependentSchemas', {}).update(dependent_schemas)

        return out

    result = migrate(payload)
    result['$schema'] = 'https://json-schema.org/draft/2020-12/schema'
    return result
