from copy import deepcopy


def transform(payload):
    components = payload.get('components', {}).get('schemas', {})
    prefix = '#/components/schemas/'

    def visit_children(schema, visit):
        properties = schema.get('properties')
        if isinstance(properties, dict):
            for name in properties:
                properties[name] = visit(properties[name])
        for keyword in ('items', 'additionalProperties', 'not'):
            if isinstance(schema.get(keyword), dict):
                schema[keyword] = visit(schema[keyword])
        for keyword in ('allOf', 'anyOf', 'oneOf'):
            if isinstance(schema.get(keyword), list):
                schema[keyword] = [visit(member) for member in schema[keyword]]
        return schema

    def resolve(schema):
        if not isinstance(schema, dict):
            return deepcopy(schema)
        ref = schema.get('$ref')
        if isinstance(ref, str) and ref.startswith(prefix):
            return resolve(components[ref[len(prefix):]])
        return visit_children(deepcopy(schema), resolve)

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
        if isinstance(values, list) and not any(value is None for value in values):
            values.append(None)

    def strict(schema):
        if not isinstance(schema, dict):
            return schema
        original_required = schema.get('required', [])
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

    return {
        name: strict(nullable(resolve(schema)))
        for name, schema in components.items()
    }
