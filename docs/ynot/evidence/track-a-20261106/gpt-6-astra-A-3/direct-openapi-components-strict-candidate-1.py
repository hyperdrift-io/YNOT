from copy import deepcopy


def transform(payload):
    components = payload.get('components', {}).get('schemas', {})
    prefix = '#/components/schemas/'

    def visit_children(schema, visit):
        properties = schema.get('properties')
        if isinstance(properties, dict):
            for name, child in list(properties.items()):
                if isinstance(child, dict):
                    properties[name] = visit(child)
        for keyword in ('items', 'additionalProperties', 'not'):
            child = schema.get(keyword)
            if isinstance(child, dict):
                schema[keyword] = visit(child)
        for keyword in ('allOf', 'anyOf', 'oneOf'):
            children = schema.get(keyword)
            if isinstance(children, list):
                schema[keyword] = [
                    visit(child) if isinstance(child, dict) else child
                    for child in children
                ]
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
        if schema.pop('nullable', None) is True:
            kind = schema.get('type')
            if isinstance(kind, str):
                schema['type'] = [kind, 'null']
        return visit_children(schema, nullable)

    def allow_null(schema):
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
        visit_children(schema, strict)
        schema.pop('default', None)
        if 'properties' in schema:
            properties = schema['properties']
            for name, child in properties.items():
                if name not in original_required and isinstance(child, dict):
                    allow_null(child)
            schema['additionalProperties'] = False
            schema['required'] = sorted(properties)
        return schema

    return {
        name: strict(nullable(resolve(schema)))
        for name, schema in components.items()
    }
