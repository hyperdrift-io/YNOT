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

    resolved = {}
    prefix = '#/components/schemas/'

    def resolve_component(name):
        if name not in resolved:
            resolved[name] = resolve(components[name])
        return deepcopy(resolved[name])

    def resolve(value):
        if not isinstance(value, dict):
            return deepcopy(value)
        ref = value.get('$ref')
        if isinstance(ref, str) and ref.startswith(prefix):
            return resolve_component(ref[len(prefix):])
        return visit_children(deepcopy(value), resolve)

    def nullable(value):
        if not isinstance(value, dict):
            return deepcopy(value)
        schema = visit_children(deepcopy(value), nullable)
        flag = schema.pop('nullable', None)
        if flag is True and isinstance(schema.get('type'), str):
            schema['type'] = [schema['type'], 'null']
        return schema

    def allow_null(schema):
        if not isinstance(schema, dict):
            return
        kind = schema.get('type')
        if isinstance(kind, str) and kind != 'null':
            schema['type'] = [kind, 'null']
        elif isinstance(kind, list) and 'null' not in kind:
            kind.append('null')
        enum = schema.get('enum')
        if isinstance(enum, list) and None not in enum:
            enum.append(None)

    def strict(value):
        if not isinstance(value, dict):
            return deepcopy(value)
        original_required = value.get('required', [])
        schema = visit_children(deepcopy(value), strict)
        schema.pop('default', None)
        if 'properties' in schema:
            properties = schema['properties']
            for name, child in properties.items():
                if name not in original_required:
                    allow_null(child)
            schema['additionalProperties'] = False
            schema['required'] = sorted(properties)
        return schema

    return {
        name: strict(nullable(resolve_component(name)))
        for name in components
    }
