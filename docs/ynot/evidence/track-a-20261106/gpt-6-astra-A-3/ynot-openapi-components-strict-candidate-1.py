from copy import deepcopy


def transform(payload):
    components = payload.get('components', {}).get('schemas', {})

    def visit_children(schema, visit):
        properties = schema.get('properties')
        if isinstance(properties, dict):
            schema['properties'] = {
                name: visit(value) for name, value in properties.items()
            }
        for key in ('items', 'additionalProperties', 'not'):
            if isinstance(schema.get(key), dict):
                schema[key] = visit(schema[key])
        for key in ('allOf', 'anyOf', 'oneOf'):
            if isinstance(schema.get(key), list):
                schema[key] = [visit(value) for value in schema[key]]
        return schema

    def resolve(schema):
        if not isinstance(schema, dict):
            return deepcopy(schema)
        ref = schema.get('$ref')
        prefix = '#/components/schemas/'
        if isinstance(ref, str) and ref.startswith(prefix):
            return resolve(components[ref[len(prefix):]])
        return visit_children(deepcopy(schema), resolve)

    def nullable(schema):
        if not isinstance(schema, dict):
            return schema
        if schema.pop('nullable', None) is True:
            value = schema.get('type')
            if isinstance(value, str):
                schema['type'] = [value, 'null']
        return visit_children(schema, nullable)

    def allow_null(schema):
        if not isinstance(schema, dict):
            return
        value = schema.get('type')
        if isinstance(value, str) and value != 'null':
            schema['type'] = [value, 'null']
        elif isinstance(value, list) and 'null' not in value:
            schema['type'] = value + ['null']
        values = schema.get('enum')
        if isinstance(values, list) and None not in values:
            schema['enum'] = values + [None]

    def strict(schema):
        if not isinstance(schema, dict):
            return schema
        original_required = set(schema.get('required', []))
        schema.pop('default', None)
        visit_children(schema, strict)
        if 'properties' in schema:
            properties = schema['properties']
            for name, value in properties.items():
                if name not in original_required:
                    allow_null(value)
            schema['additionalProperties'] = False
            schema['required'] = sorted(properties)
        return schema

    return {
        name: strict(nullable(resolve(schema)))
        for name, schema in components.items()
    }
