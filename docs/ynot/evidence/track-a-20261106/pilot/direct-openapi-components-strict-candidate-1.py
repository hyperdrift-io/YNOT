from copy import deepcopy


def transform(payload):
    components = payload.get('components', {}).get('schemas', {})
    prefix = '#/components/schemas/'

    def visit_children(schema, visit):
        properties = schema.get('properties')
        if isinstance(properties, dict):
            for name in properties:
                properties[name] = visit(properties[name])
        for key in ('items', 'additionalProperties', 'not'):
            if isinstance(schema.get(key), dict):
                schema[key] = visit(schema[key])
        for key in ('allOf', 'anyOf', 'oneOf'):
            if isinstance(schema.get(key), list):
                schema[key] = [visit(child) for child in schema[key]]
        return schema

    def resolve(schema):
        if not isinstance(schema, dict):
            return deepcopy(schema)
        ref = schema.get('$ref')
        if isinstance(ref, str) and ref.startswith(prefix):
            name = ref[len(prefix):].replace('~1', '/').replace('~0', '~')
            return resolve(components[name])
        return visit_children(deepcopy(schema), resolve)

    def nullable(schema):
        if not isinstance(schema, dict):
            return schema
        if schema.pop('nullable', None) is True and isinstance(schema.get('type'), str):
            schema['type'] = [schema['type'], 'null']
        return visit_children(schema, nullable)

    def permit_null(schema):
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
        original_required = set(original_required) if isinstance(original_required, list) else set()
        schema.pop('default', None)
        visit_children(schema, strict)
        if 'properties' in schema:
            properties = schema['properties']
            for name, child in properties.items():
                if name not in original_required:
                    permit_null(child)
            schema['additionalProperties'] = False
            schema['required'] = sorted(properties)
        return schema

    return {name: strict(nullable(resolve(schema))) for name, schema in components.items()}
