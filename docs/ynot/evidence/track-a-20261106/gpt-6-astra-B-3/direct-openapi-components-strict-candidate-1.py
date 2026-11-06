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

    def resolve(value):
        if not isinstance(value, dict):
            return deepcopy(value)
        ref = value.get('$ref')
        prefix = '#/components/schemas/'
        if isinstance(ref, str) and ref.startswith(prefix):
            name = ref[len(prefix):].replace('~1', '/').replace('~0', '~')
            return resolve(components[name])
        return visit_children(deepcopy(value), resolve)

    def nullable(value):
        if not isinstance(value, dict):
            return value
        flag = value.pop('nullable', None)
        if flag is True and isinstance(value.get('type'), str):
            value['type'] = [value['type'], 'null']
        return visit_children(value, nullable)

    def allow_null(schema):
        if not isinstance(schema, dict):
            return
        kind = schema.get('type')
        if isinstance(kind, str) and kind != 'null':
            schema['type'] = [kind, 'null']
        elif isinstance(kind, list) and 'null' not in kind:
            kind.append('null')
        values = schema.get('enum')
        if isinstance(values, list) and not any(v is None for v in values):
            values.append(None)

    def strict(value):
        if not isinstance(value, dict):
            return value
        original_required = value.get('required', [])
        value.pop('default', None)
        visit_children(value, strict)
        properties = value.get('properties')
        if isinstance(properties, dict):
            for name, schema in properties.items():
                if name not in original_required:
                    allow_null(schema)
            value['additionalProperties'] = False
            value['required'] = sorted(properties)
        return value

    return {
        name: strict(nullable(resolve(schema)))
        for name, schema in components.items()
    }
