from copy import deepcopy


def transform(payload):
    components = payload.get('components', {}).get('schemas', {})
    prefix = '#/components/schemas/'

    def visit_children(schema, visit):
        if not isinstance(schema, dict):
            return schema
        properties = schema.get('properties')
        if isinstance(properties, dict):
            schema['properties'] = {
                name: visit(child) for name, child in properties.items()
            }
        for keyword in ('items', 'additionalProperties', 'not'):
            if isinstance(schema.get(keyword), dict):
                schema[keyword] = visit(schema[keyword])
        for keyword in ('allOf', 'anyOf', 'oneOf'):
            if isinstance(schema.get(keyword), list):
                schema[keyword] = [visit(child) for child in schema[keyword]]
        return schema

    def resolve(schema):
        if isinstance(schema, dict):
            ref = schema.get('$ref')
            if isinstance(ref, str) and ref.startswith(prefix):
                name = ref[len(prefix):].replace('~1', '/').replace('~0', '~')
                return resolve(deepcopy(components[name]))
        return visit_children(schema, resolve)

    def nullable(schema):
        if not isinstance(schema, dict):
            return schema
        if schema.get('nullable') is True and isinstance(schema.get('type'), str):
            schema['type'] = [schema['type'], 'null']
        schema.pop('nullable', None)
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
        if isinstance(values, list) and None not in values:
            values.append(None)

    def strict(schema):
        if not isinstance(schema, dict):
            return schema
        original_required = set(schema.get('required', []))
        schema.pop('default', None)
        visit_children(schema, strict)
        if 'properties' in schema:
            properties = schema['properties']
            for name, child in properties.items():
                if name not in original_required:
                    allow_null(child)
            schema['additionalProperties'] = False
            schema['required'] = sorted(properties)
        return schema

    result = {name: resolve(deepcopy(schema)) for name, schema in components.items()}
    result = {name: nullable(schema) for name, schema in result.items()}
    return {name: strict(schema) for name, schema in result.items()}
