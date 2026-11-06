from copy import deepcopy


def _children(schema, visit):
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


def transform(payload):
    components = payload.get('components', {}).get('schemas', {})
    prefix = '#/components/schemas/'

    def resolve(schema):
        if not isinstance(schema, dict):
            return schema
        ref = schema.get('$ref')
        if isinstance(ref, str) and ref.startswith(prefix):
            return resolve(deepcopy(components[ref[len(prefix):]]))
        return _children(schema, resolve)

    def nullable(schema):
        if not isinstance(schema, dict):
            return schema
        flag = schema.pop('nullable', None)
        if flag is True and isinstance(schema.get('type'), str):
            schema['type'] = [schema['type'], 'null']
        return _children(schema, nullable)

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

    def strict(schema):
        if not isinstance(schema, dict):
            return schema
        original_required = set(schema.get('required', []))
        schema.pop('default', None)
        _children(schema, strict)
        properties = schema.get('properties')
        if isinstance(properties, dict):
            for name, value in properties.items():
                if name not in original_required:
                    allow_null(value)
            schema['additionalProperties'] = False
            schema['required'] = sorted(properties)
        return schema

    resolved = {
        name: resolve(deepcopy(schema))
        for name, schema in components.items()
    }
    for schema in resolved.values():
        nullable(schema)
    for schema in resolved.values():
        strict(schema)
    return resolved
