from copy import deepcopy


def transform(payload):
    result = deepcopy(payload)

    def visit(schema):
        schema.pop('default', None)

        if 'properties' in schema:
            properties = schema['properties']
            original_required = set(schema.get('required', []))
            for name, child in properties.items():
                if name not in original_required:
                    kind = child['type']
                    if isinstance(kind, str):
                        if kind != 'null':
                            child['type'] = [kind, 'null']
                    elif 'null' not in kind:
                        child['type'] = kind + ['null']
                    if 'enum' in child and not any(
                        value is None for value in child['enum']
                    ):
                        child['enum'].append(None)
                visit(child)
            schema['additionalProperties'] = False
            schema['required'] = sorted(properties)

        items = schema.get('items')
        if isinstance(items, dict):
            visit(items)
        elif isinstance(items, list):
            for child in items:
                if isinstance(child, dict):
                    visit(child)

        for child in schema.get('anyOf', []):
            if isinstance(child, dict):
                visit(child)

    visit(result)
    return result
