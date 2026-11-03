from copy import deepcopy


def transform(payload):
    def migrate(schema):
        if not isinstance(schema, dict):
            return schema

        # Traverse only draft-04 schema positions, never instance data.
        for keyword in ('properties', 'patternProperties', 'definitions'):
            mapping = schema.get(keyword)
            if isinstance(mapping, dict):
                for name, child in mapping.items():
                    mapping[name] = migrate(child)

        dependencies = schema.get('dependencies')
        if isinstance(dependencies, dict):
            for name, child in dependencies.items():
                if isinstance(child, (dict, bool)):
                    dependencies[name] = migrate(child)

        items = schema.get('items')
        if isinstance(items, list):
            schema['items'] = [migrate(child) for child in items]
        elif isinstance(items, (dict, bool)):
            schema['items'] = migrate(items)

        for keyword in ('additionalItems', 'additionalProperties', 'not'):
            if isinstance(schema.get(keyword), dict):
                schema[keyword] = migrate(schema[keyword])

        for keyword in ('allOf', 'anyOf', 'oneOf'):
            if isinstance(schema.get(keyword), list):
                schema[keyword] = [migrate(child) for child in schema[keyword]]

        if 'id' in schema:
            schema['$id'] = schema.pop('id')
        if 'definitions' in schema:
            schema['$defs'] = schema.pop('definitions')

        ref = schema.get('$ref')
        if isinstance(ref, str) and ref.startswith('#/definitions/'):
            schema['$ref'] = '#/$defs/' + ref[len('#/definitions/'):]

        for exclusive, bound in (
            ('exclusiveMinimum', 'minimum'),
            ('exclusiveMaximum', 'maximum'),
        ):
            value = schema.get(exclusive)
            if value is True:
                if bound in schema:
                    schema[exclusive] = schema.pop(bound)
                else:
                    schema.pop(exclusive)
            elif value is False:
                schema.pop(exclusive)

        if isinstance(schema.get('items'), list):
            schema['prefixItems'] = schema.pop('items')
            if 'additionalItems' in schema:
                schema['items'] = schema.pop('additionalItems')
        else:
            schema.pop('additionalItems', None)

        if isinstance(dependencies, dict):
            required = {}
            dependent_schemas = {}
            for name, value in dependencies.items():
                if isinstance(value, list) and all(isinstance(v, str) for v in value):
                    required[name] = value
                else:
                    dependent_schemas[name] = value
            schema.pop('dependencies')
            if required:
                schema['dependentRequired'] = required
            if dependent_schemas:
                schema['dependentSchemas'] = dependent_schemas

        return schema

    result = migrate(deepcopy(payload))
    if isinstance(result, dict):
        result['$schema'] = 'https://json-schema.org/draft/2020-12/schema'
    return result
