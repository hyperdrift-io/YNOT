from copy import deepcopy


def transform(payload):
    components = payload.get('components', {}).get('schemas', {})
    prefix = '#/components/schemas/'
    resolved = {}

    def visit_children(schema, visit):
        properties = schema.get('properties')
        if isinstance(properties, dict):
            schema['properties'] = {
                name: visit(child) for name, child in properties.items()
            }
        for key in ('items', 'additionalProperties', 'not'):
            if isinstance(schema.get(key), dict):
                schema[key] = visit(schema[key])
        for key in ('allOf', 'anyOf', 'oneOf'):
            if isinstance(schema.get(key), list):
                schema[key] = [visit(child) for child in schema[key]]
        return schema

    def resolve_component(name):
        if name not in resolved:
            resolved[name] = resolve(components[name])
        return deepcopy(resolved[name])

    def resolve(schema):
        if not isinstance(schema, dict):
            return deepcopy(schema)
        ref = schema.get('$ref')
        if isinstance(ref, str) and ref.startswith(prefix):
            return resolve_component(ref[len(prefix):])
        return visit_children(deepcopy(schema), resolve)

    def nullable(schema):
        if not isinstance(schema, dict):
            return schema
        if schema.pop('nullable', None) is True:
            if isinstance(schema.get('type'), str):
                schema['type'] = [schema['type'], 'null']
        return visit_children(schema, nullable)

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
        schema.pop('default', None)
        original_required = schema.get('required', [])
        visit_children(schema, strict)
        if 'properties' in schema:
            properties = schema['properties']
            for name, child in properties.items():
                if name not in original_required:
                    allow_null(child)
            schema['additionalProperties'] = False
            schema['required'] = sorted(properties)
        return schema

    result = {name: resolve_component(name) for name in components}
    result = {name: nullable(schema) for name, schema in result.items()}
    return {name: strict(schema) for name, schema in result.items()}
