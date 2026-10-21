"""SDMM validator: JSON Schema (minimal draft-2020 subset) + relationship-registry rules.

No third-party dependencies. The schema subset covers only the keywords used in
schema/mapping.schema.json; `check_schema` is not a general JSON Schema engine.
"""
from pathlib import Path
import argparse, json, re, sys

ROOT = Path(__file__).resolve().parents[1]
RULES = ROOT / 'schema' / 'relationship-types.json'
SCHEMA = ROOT / 'schema' / 'mapping.schema.json'

STATUSES = {'proposed', 'validated', 'needs_review', 'approved', 'rejected', 'superseded'}
REVIEWED_STATUSES = {'approved', 'rejected', 'superseded'}
LAYER = re.compile(r'^L([0-3])\.')

EXIT_OK, EXIT_ISSUES, EXIT_USAGE = 0, 1, 2


def load_registry(path=RULES):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def load_schema(path=SCHEMA):
    return json.loads(Path(path).read_text(encoding='utf-8'))


# ---------------------------------------------------------------- JSON Schema subset

_TYPES = {
    'object': lambda v: isinstance(v, dict),
    'array': lambda v: isinstance(v, list),
    'string': lambda v: isinstance(v, str),
    'number': lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    'integer': lambda v: isinstance(v, int) and not isinstance(v, bool),
    'boolean': lambda v: isinstance(v, bool),
    'null': lambda v: v is None,
}


def check_schema(value, schema, root=None, path='$'):
    """Return a list of '<path>: <problem>' strings for `value` against `schema`."""
    root = root if root is not None else schema
    if '$ref' in schema:
        node = root
        for part in schema['$ref'].lstrip('#/').split('/'):
            node = node[part]
        return check_schema(value, node, root, path)
    issues = []
    if 'enum' in schema and value not in schema['enum']:
        return [f'{path}: must be one of {schema["enum"]}']
    if 'type' in schema and not _TYPES[schema['type']](value):
        return [f'{path}: expected {schema["type"]}']
    if isinstance(value, dict):
        props = schema.get('properties', {})
        for key in schema.get('required', []):
            if key not in value:
                issues.append(f'{path}: missing required property {key!r}')
        if schema.get('additionalProperties') is False:
            for key in sorted(set(value) - set(props)):
                issues.append(f'{path}: unknown property {key!r}')
        for key, sub in props.items():
            if key in value:
                issues += check_schema(value[key], sub, root, f'{path}.{key}')
    elif isinstance(value, list):
        if len(value) < schema.get('minItems', 0):
            issues.append(f'{path}: requires at least {schema["minItems"]} item(s)')
        if 'items' in schema:
            for i, item in enumerate(value):
                issues += check_schema(item, schema['items'], root, f'{path}[{i}]')
    elif isinstance(value, str):
        # Stricter than JSON Schema: whitespace-only strings count as empty.
        if len(value.strip()) < schema.get('minLength', 0):
            issues.append(f'{path}: must not be empty')
        if 'pattern' in schema and not re.search(schema['pattern'], value):
            issues.append(f'{path}: does not match pattern {schema["pattern"]}')
    elif _TYPES['number'](value):
        if 'minimum' in schema and value < schema['minimum']:
            issues.append(f'{path}: must be >= {schema["minimum"]}')
        if 'maximum' in schema and value > schema['maximum']:
            issues.append(f'{path}: must be <= {schema["maximum"]}')
    return issues


# ---------------------------------------------------------------- registry self-check

def validate_registry(registry):
    issues = []
    perspectives = set(registry.get('perspectives', []))
    authorities = set(registry.get('authorities', []))
    seen_edges, seen_ids = set(), set()
    for pos, rule in enumerate(registry.get('relationships', []), 1):
        prefix = f"rule #{pos} ({rule.get('mapping_type_id', '?')})"
        for key in ('mapping_type_id', 'source_type', 'relationship', 'target_type', 'perspective',
                    'authority', 'cardinality', 'direction_semantics', 'required_evidence',
                    'rule_version', 'owner'):
            if not rule.get(key):
                issues.append(f'{prefix}: missing {key}')
        edge = (rule.get('source_type'), rule.get('relationship'), rule.get('target_type'))
        if edge in seen_edges:
            issues.append(f'{prefix}: duplicate edge {edge}')
        seen_edges.add(edge)
        if rule.get('mapping_type_id') in seen_ids:
            issues.append(f'{prefix}: duplicate mapping_type_id')
        seen_ids.add(rule.get('mapping_type_id'))
        src, tgt = LAYER.match(rule.get('source_type') or ''), LAYER.match(rule.get('target_type') or '')
        if not src or not tgt:
            issues.append(f'{prefix}: source/target types must be prefixed L0.-L3.')
        elif int(tgt.group(1)) - int(src.group(1)) != 1:
            issues.append(f'{prefix}: cross-layer edges must point from L(n) to L(n+1)')
        if rule.get('perspective') not in perspectives:
            issues.append(f'{prefix}: perspective must be one of {sorted(perspectives)}')
        if rule.get('authority') not in authorities:
            issues.append(f'{prefix}: authority must be one of {sorted(authorities)}')
    return issues


# ---------------------------------------------------------------- mapping rules

def validate(payload, registry=None, schema=None, resolver=None):
    """Validate one mapping document. Returns a list of issue strings (empty = valid)."""
    registry = registry or load_registry()
    schema = schema or load_schema()
    issues = check_schema(payload, schema)
    if not isinstance(payload, dict) or not isinstance(payload.get('mappings'), list):
        return issues  # structure too broken for rule checks
    rules = {(r['source_type'], r['relationship'], r['target_type']): r for r in registry['relationships']}
    registry_version = registry.get('$schema_version')
    if payload.get('registry_version') and payload['registry_version'] != registry_version:
        issues.append(f"document registry_version {payload['registry_version']!r} does not match loaded registry {registry_version!r}")
    mappings = [m for m in payload['mappings'] if isinstance(m, dict)]
    ids = [m.get('mapping_id') for m in mappings if isinstance(m.get('mapping_id'), str) and m['mapping_id']]
    id_set = set(ids)
    successors = {m['previous_mapping_id'] for m in mappings if isinstance(m.get('previous_mapping_id'), str)}
    for pos, mapping in enumerate(mappings, 1):
        mid = mapping.get('mapping_id')
        prefix = f"mapping #{pos}" + (f" ({mid})" if mid else '')
        if mid and ids.count(mid) > 1:
            issues.append(f'{prefix}: duplicate mapping_id')
        source, target = mapping.get('source') or {}, mapping.get('target') or {}
        edge = (source.get('type'), mapping.get('relationship'), target.get('type'))
        rule = rules.get(edge)
        if rule is None:
            issues.append(f'{prefix}: relationship {edge} is not in the registry')
        else:
            if mapping.get('perspective') and mapping['perspective'] != rule['perspective']:
                issues.append(f"{prefix}: perspective {mapping['perspective']!r} does not match registry {rule['perspective']!r}")
            if rule['authority'].startswith('bian_') and not mapping.get('bian_release'):
                issues.append(f"{prefix}: {rule['authority']} mapping requires bian_release")
        status = mapping.get('status')
        if status in REVIEWED_STATUSES and not mapping.get('reviewer_id'):
            issues.append(f'{prefix}: {status} mapping requires reviewer_id')
        if status == 'superseded' and mid not in successors:
            issues.append(f'{prefix}: superseded mapping has no successor referencing it via previous_mapping_id')
        prev = mapping.get('previous_mapping_id')
        if prev and prev not in id_set:
            issues.append(f'{prefix}: previous_mapping_id {prev!r} not found in document')
        if prev == mid:
            issues.append(f'{prefix}: previous_mapping_id cannot reference itself')
        if resolver is not None and mapping.get('bian_release'):
            for label, ent in (('source', source), ('target', target)):
                cid = ent.get('canonical_id')
                if cid and resolver.resolve(cid, mapping['bian_release']) is None:
                    issues.append(f"{prefix}: {label} canonical_id {cid!r} not found in BIAN release {mapping['bian_release']!r}")
    return issues


def validate_files(paths, registry=None, schema=None, resolver=None):
    """Validate several documents; mapping_ids must be unique across all of them."""
    registry = registry or load_registry()
    schema = schema or load_schema()
    report, seen = {}, {}
    for path in paths:
        path = Path(path)
        try:
            payload = json.loads(path.read_text(encoding='utf-8'))
        except (OSError, ValueError) as exc:
            report[str(path)] = [f'cannot read: {exc}']
            continue
        issues = validate(payload, registry, schema, resolver)
        for m in (payload.get('mappings') or []) if isinstance(payload, dict) else []:
            mid = m.get('mapping_id') if isinstance(m, dict) else None
            if mid and mid in seen and seen[mid] != str(path):
                issues.append(f'mapping_id {mid!r} also defined in {seen[mid]}')
            elif mid:
                seen[mid] = str(path)
        report[str(path)] = issues
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(prog='sdmm-validate', description='Validate SDMM mapping documents.')
    parser.add_argument('paths', nargs='+', help='mapping JSON file(s)')
    parser.add_argument('--registry', default=RULES, help='relationship registry (default: bundled)')
    parser.add_argument('--json', action='store_true', help='emit a JSON report instead of text')
    args = parser.parse_args(argv)
    try:
        registry = load_registry(args.registry)
    except (OSError, ValueError) as exc:
        print(f'ERROR: cannot load registry {args.registry}: {exc}', file=sys.stderr)
        return EXIT_USAGE
    registry_issues = validate_registry(registry)
    report = validate_files(args.paths, registry)
    if registry_issues:
        report = {'<registry>': registry_issues, **report}
    failed = any(report.values())
    if args.json:
        print(json.dumps({'ok': not failed, 'registry_version': registry.get('$schema_version'), 'files': report}, indent=2))
    else:
        for path, issues in report.items():
            for issue in issues:
                print(f'ERROR: {path}: {issue}')
            if not issues:
                print(f'OK: {path}')
    return EXIT_ISSUES if failed else EXIT_OK


if __name__ == '__main__':
    raise SystemExit(main())
