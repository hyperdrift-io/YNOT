from copy import deepcopy


def transform(payload):
    components = payload.get('components', {}).get('schemas', {})
    prefix = '#/components/schemas/'

    def children(schema, visit):
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
            return schema
        ref = schema.get('$ref')
        if isinstance(ref, str) and ref.startswith(prefix):
            name = ref[len(prefix):].replace('~1', '/').replace('~0', '~')
            return resolve(deepcopy(components[name]))
        return children(schema, resolve)

    def nullable(schema):
        if not isinstance(schema, dict):
            return schema
        allows_null = schema.pop('nullable', None)
        if allows_null is True and isinstance(schema.get('type'), str):
            schema['type'] = [schema['type'], 'null']
        return children(schema, nullable)

    def optional(schema):
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
        original_required = schema.get('required', [])
        schema.pop('default', None)
        children(schema, strict)
        if 'properties' in schema:
            properties = schema['properties']
            for name, value in properties.items():
                if name not in original_required:
                    optional(value)
            schema['additionalProperties'] = False
            schema['required'] = sorted(properties)
        return schema

    return {
        name: strict(nullable(resolve(deepcopy(schema))))
        for name, schema in components.items()
    }
