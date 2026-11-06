from copy import deepcopy


def transform(payload):
    def migrate(schema):
        if not isinstance(schema, dict):
            return deepcopy(schema)
        out = deepcopy(schema)

        for keyword in ('properties', 'patternProperties', 'definitions'):
            if isinstance(schema.get(keyword), dict):
                out[keyword] = {name: migrate(value) for name, value in schema[keyword].items()}

        for keyword in ('items', 'additionalItems', 'additionalProperties', 'not'):
            value = schema.get(keyword)
            if isinstance(value, dict):
                out[keyword] = migrate(value)
            elif keyword == 'items' and isinstance(value, list):
                out[keyword] = [migrate(member) for member in value]

        for keyword in ('allOf', 'anyOf', 'oneOf'):
            if isinstance(schema.get(keyword), list):
                out[keyword] = [migrate(member) for member in schema[keyword]]

        if 'id' in out:
            out['$id'] = out.pop('id')
        if 'definitions' in out:
            out['$defs'] = out.pop('definitions')
        ref = out.get('$ref')
        if isinstance(ref, str) and ref.startswith('#/definitions/'):
            out['$ref'] = '#/$defs/' + ref[len('#/definitions/'):]

        for exclusive, inclusive in (('exclusiveMinimum', 'minimum'), ('exclusiveMaximum', 'maximum')):
            if out.get(exclusive) is True:
                if inclusive in out:
                    out[exclusive] = out.pop(inclusive)
                else:
                    out.pop(exclusive)
            elif out.get(exclusive) is False:
                out.pop(exclusive)

        if isinstance(schema.get('items'), list):
            out['prefixItems'] = out.pop('items')
            if 'additionalItems' in out:
                out['items'] = out.pop('additionalItems')
        else:
            out.pop('additionalItems', None)

        if 'dependencies' in schema:
            required = {}
            dependent = {}
            for name, value in schema['dependencies'].items():
                if isinstance(value, list):
                    required[name] = deepcopy(value)
                else:
                    dependent[name] = migrate(value)
            out.pop('dependencies')
            if required:
                out['dependentRequired'] = required
            if dependent:
                out['dependentSchemas'] = dependent
        return out

    result = migrate(payload)
    if isinstance(result, dict):
        result['$schema'] = 'https://json-schema.org/draft/2020-12/schema'
    return result
