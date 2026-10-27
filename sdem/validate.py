"""SDEM validator: JSON Schema (minimal draft-2020 subset) + relationship-registry rules.

No third-party dependencies. The schema subset covers only the keywords used in
schema/relationship-registry.schema.json; `check_schema` is not a general JSON Schema engine.
"""
from pathlib import Path
import argparse, json, re, sys
from sdem.metamodel import Metamodel

from sdem.paths import DATA_ROOT as ROOT  # repository folders, or bundled copies when installed
RULES = ROOT / 'schema' / 'relationship-types.json'
SCHEMA = ROOT / 'schema' / 'relationship-registry.schema.json'

STATUSES = {'proposed', 'validated', 'needs_review', 'approved', 'rejected', 'superseded'}
REVIEWED_STATUSES = {'approved', 'rejected', 'superseded'}
# CTL-21: names that are agents or tools, never a person (sdem-* agent names are caught by prefix)
NON_PERSON_REVIEWERS = {'architect', 'agent', 'copilot', 'github-copilot', 'engine', 'orchestrator', 'sdem', 'rules-engine', 'ai'}
TYPE_PREFIX = re.compile(r'^([A-Za-z0-9]+)\.')

EXIT_OK, EXIT_ISSUES, EXIT_USAGE = 0, 1, 2


def load_registry(path=RULES):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def load_schema(path=SCHEMA):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def level_codes(registry):
    return [lv['code'] if isinstance(lv, dict) else lv for lv in registry.get('levels', [])]


def normalize_type(t, registry):
    """Apply the registry's type_aliases (e.g. 'L1.' -> 'A2.') so older documents keep validating."""
    if not isinstance(t, str):
        return t
    for old, new in registry.get('type_aliases', {}).items():
        if t.startswith(old):
            return new + t[len(old):]
    return t


def level_of(t, registry):
    m = TYPE_PREFIX.match(normalize_type(t, registry) or '')
    return m.group(1) if m else None


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

def validate_registry(registry, metamodel=None):
    metamodel = metamodel or Metamodel.load()
    issues = []
    perspectives = set(registry.get('perspectives', []))
    authorities = set(registry.get('authorities', []))
    seen_edges, seen_ids = set(), set()
    if not level_codes(registry):
        issues.append('registry: missing ordered levels list')
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
        levels = level_codes(registry)
        src, tgt = level_of(rule.get('source_type'), registry), level_of(rule.get('target_type'), registry)
        if src not in levels or tgt not in levels:
            issues.append(f'{prefix}: source/target types must be prefixed with a level code {levels}')
        elif levels.index(tgt) - levels.index(src) != 1:
            issues.append(f'{prefix}: cross-level edges must point from A(n) to A(n+1)')
        for key in ('source_type', 'target_type'):
            if rule.get(key) and not metamodel.known(normalize_type(rule[key], registry)):
                issues.append(f'{prefix}: {key} {rule[key]!r} is not in the metamodel')
        if str(rule.get('authority', '')).startswith('bian_'):
            ends = [metamodel.entities.get(normalize_type(rule.get(k), registry), {}) for k in ('source_type', 'target_type')]
            if not any(str(e.get('definition_source', '')).startswith('bian_') for e in ends):
                issues.append(f'{prefix}: bian_* authority but neither endpoint entity has a bian_* definition_source')
        if rule.get('perspective') not in perspectives:
            issues.append(f'{prefix}: perspective must be one of {sorted(perspectives)}')
        if rule.get('authority') not in authorities:
            issues.append(f'{prefix}: authority must be one of {sorted(authorities)}')
    return issues


# ---------------------------------------------------------------- mapping rules

EVIDENCE_KIND = re.compile(r'^[a-z][a-z0-9_]*$')


def split_evidence(ref):
    """'kind:REF' -> ('kind', 'REF'); anything else -> (None, ref). Kinds are snake_case tokens."""
    kind, sep, rest = ref.partition(':')
    if sep and EVIDENCE_KIND.match(kind) and rest.strip():
        return kind, rest.strip()
    return None, ref


def match_rule(rules, metamodel, src, rel, tgt):
    """Exact triple first; otherwise any rule with the same relationship whose endpoints are ancestors (is-a)."""
    if (src, rel, tgt) in rules:
        return rules[(src, rel, tgt)]
    for (rs, rr, rt), rule in rules.items():
        if rr == rel and metamodel.is_a(src, rs) and metamodel.is_a(tgt, rt):
            return rule
    return None


def validate(payload, registry=None, schema=None, resolver=None, entity_resolver=None, warnings=None, verdicts=None, metamodel=None):
    """Validate one mapping document. Returns a list of issue strings (empty = valid).

    `resolver`         optional ReferenceResolver: canonical_ids on BIAN-grounded mappings must resolve.
    `entity_resolver`  optional EntityResolver: every endpoint must exist in the level models.
    `warnings`         optional list; advisory findings are appended to it instead of being returned.
    `verdicts`         optional dict; filled with {mapping_id: {structural, governance, referential, bian, semantic}}.
    """
    registry = registry or load_registry()
    schema = schema or load_schema()
    metamodel = metamodel or Metamodel.load()
    warnings = warnings if warnings is not None else []
    verdicts = verdicts if verdicts is not None else {}
    issues = check_schema(payload, schema)
    if not isinstance(payload, dict) or not isinstance(payload.get('mappings'), list):
        return issues  # structure too broken for rule checks
    rules = {(r['source_type'], r['relationship'], r['target_type']): r for r in registry['relationships']}
    registry_version = registry.get('$schema_version')
    if payload.get('registry_version') and payload['registry_version'] != registry_version:
        issues.append(f"document registry_version {payload['registry_version']!r} does not match loaded registry {registry_version!r}")
    if payload.get('metamodel_version') and payload['metamodel_version'] != metamodel.version:
        issues.append(f"document metamodel_version {payload['metamodel_version']!r} does not match loaded metamodel {metamodel.version!r}")
    mappings = [m for m in payload['mappings'] if isinstance(m, dict)]
    ids = [m.get('mapping_id') for m in mappings if isinstance(m.get('mapping_id'), str) and m['mapping_id']]
    id_set = set(ids)
    successors = {m['previous_mapping_id'] for m in mappings if isinstance(m.get('previous_mapping_id'), str)}
    bian_level = registry.get('bian_level', 'A2')
    for pos, mapping in enumerate(mappings, 1):
        mid = mapping.get('mapping_id')
        prefix = f"mapping #{pos}" + (f" ({mid})" if mid else '')
        v = {'structural': 'pass', 'governance': 'pass',
             'referential': 'unverified' if entity_resolver is None else 'pass',
             'bian': 'unverified', 'semantic': 'unverified'}
        def fail(cat, msg):
            issues.append(f'{prefix}: {msg}'); v[cat] = 'fail'
        if mid and ids.count(mid) > 1:
            fail('structural', 'duplicate mapping_id')
        source, target = mapping.get('source') or {}, mapping.get('target') or {}
        stype, ttype = normalize_type(source.get('type'), registry), normalize_type(target.get('type'), registry)
        for label, t in (('source', stype), ('target', ttype)):
            if t and not metamodel.known(t):
                fail('structural', f"{label} entity {t!r} is not in the metamodel")
            elif t and metamodel.is_artefact(t):
                fail('structural', f"{label} entity {t!r} is an artefact; artefacts may be cited as evidence but not used as endpoints")
        rule = match_rule(rules, metamodel, stype, mapping.get('relationship'), ttype) if v['structural'] == 'pass' else None
        if rule is None:
            if v['structural'] == 'pass':
                fail('structural', f"relationship ({stype}, {mapping.get('relationship')}, {ttype}) is not in the registry")
        else:
            if mapping.get('perspective') and mapping['perspective'] != rule['perspective']:
                fail('structural', f"perspective {mapping['perspective']!r} does not match registry {rule['perspective']!r}")
            if rule['authority'].startswith('bian_'):
                # Proposals are drafts: BIAN anchoring is required at approval, flagged until then.
                draft = mapping.get('status') == 'proposed'
                report = (lambda msg: warnings.append(f'{prefix}: {msg}; must be supplied before approval')) if draft else (lambda msg: fail('governance', msg))
                if not mapping.get('bian_release'):
                    report(f"{rule['authority']} mapping requires bian_release")
                for label, ent in (('source', source), ('target', target)):
                    if level_of(ent.get('type'), registry) == bian_level and not ent.get('canonical_id'):
                        report(f"{rule['authority']} mapping requires canonical_id on its {bian_level} {label}")
            required = set(rule.get('required_evidence', []))
            refs = [r for r in mapping.get('evidence', []) if isinstance(r, str)]
            kinds = {k for k, _ in map(split_evidence, refs) if k}
            if required and kinds:
                missing = sorted(required - kinds)
                if missing and mapping.get('status') == 'proposed':
                    warnings.append(f"{prefix}: proposal lacks required evidence kind(s) {missing}; must be supplied before approval")
                elif missing:
                    fail('governance', f"evidence missing required kind(s) {missing}")
            elif required and refs:
                warnings.append(f"{prefix}: evidence is untyped; cannot confirm required kind(s) {sorted(required)} (use 'kind:ref')")
        status = mapping.get('status')
        if status in ('approved', 'validated') and (str(mapping.get('mapping_id', '')).startswith(('PRJ-', 'DSN-')) or any(str((e or {}).get('id', '')).startswith(('PRJ-', 'DSN-')) for e in (source, target))):
            fail('governance', 'a link to a projected or design record cannot be approved or validated (CTL-16)')
        if status in REVIEWED_STATUSES:
            for field in ('reviewer_id', 'approved_at'):
                if not mapping.get(field):
                    fail('governance', f'{status} mapping requires {field}')
            rv = str(mapping.get('reviewer_id') or '').strip().lower()
            if rv and (rv.startswith('sdem-') or rv in NON_PERSON_REVIEWERS or rv == str(mapping.get('created_by') or '').strip().lower()):
                fail('governance', f"reviewer_id {mapping.get('reviewer_id')!r} is an agent or a tool — a link is approved by a person (CTL-21)")
        if status == 'superseded' and mid not in successors:
            fail('governance', 'superseded mapping has no successor referencing it via previous_mapping_id')
        prev = mapping.get('previous_mapping_id')
        if prev and prev not in id_set:
            fail('governance', f'previous_mapping_id {prev!r} not found in document')
        if prev == mid:
            fail('governance', 'previous_mapping_id cannot reference itself')
        if resolver is not None and mapping.get('bian_release'):
            v['bian'] = 'pass'
            for label, ent in (('source', source), ('target', target)):
                cid = ent.get('canonical_id')
                if cid and resolver.resolve(cid, mapping['bian_release']) is None:
                    fail('bian', f"{label} canonical_id {cid!r} not found in BIAN release {mapping['bian_release']!r}")
        if entity_resolver is not None:
            for label, ent in (('source', source), ('target', target)):
                if all(isinstance(ent.get(k), str) for k in ('id', 'type', 'version')):
                    ntype = normalize_type(ent['type'], registry)
                    if entity_resolver.resolve_entity(ent['id'], ntype, ent['version']) is None:
                        fail('referential', f"{label} {ntype} {ent['id']}@{ent['version']} not found in level model")
        if mid:
            verdicts[mid] = v
    return issues


def validate_files(paths, registry=None, schema=None, resolver=None, entity_resolver=None, warnings=None, verdicts=None, metamodel=None):
    """Validate several documents; mapping_ids must be unique across all of them."""
    registry = registry or load_registry()
    schema = schema or load_schema()
    warnings = warnings if warnings is not None else {}
    verdicts = verdicts if verdicts is not None else {}
    metamodel = metamodel or Metamodel.load()
    report, seen = {}, {}
    for path in paths:
        path = Path(path)
        try:
            payload = json.loads(path.read_text(encoding='utf-8'))
        except (OSError, ValueError) as exc:
            report[str(path)] = [f'cannot read: {exc}']
            continue
        file_warnings, file_verdicts = [], {}
        issues = validate(payload, registry, schema, resolver, entity_resolver, file_warnings, file_verdicts, metamodel)
        verdicts[str(path)] = file_verdicts
        if file_warnings:
            warnings[str(path)] = file_warnings
        for m in (payload.get('mappings') or []) if isinstance(payload, dict) else []:
            mid = m.get('mapping_id') if isinstance(m, dict) else None
            if mid and mid in seen and seen[mid] != str(path):
                issues.append(f'mapping_id {mid!r} also defined in {seen[mid]}')
            elif mid:
                seen[mid] = str(path)
        report[str(path)] = issues
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(prog='sdem-validate', description='Validate SDEM mapping documents.')
    parser.add_argument('paths', nargs='+', help='mapping JSON file(s)')
    parser.add_argument('--registry', default=RULES, help='relationship registry (default: bundled)')
    parser.add_argument('--catalogue', help='entity catalogue JSON; every endpoint must exist in it')
    parser.add_argument('--strict', action='store_true', help='treat warnings as errors (except draft warnings on proposed records)')
    parser.add_argument('--json', action='store_true', help='emit a JSON report instead of text')
    args = parser.parse_args(argv)
    try:
        registry = load_registry(args.registry)
        entity_resolver = None
        if args.catalogue:
            from sdem.reference import CatalogueEntityResolver
            entity_resolver = CatalogueEntityResolver.from_file(args.catalogue)
    except (OSError, ValueError, KeyError) as exc:
        print(f'ERROR: cannot load inputs: {exc}', file=sys.stderr)
        return EXIT_USAGE
    metamodel = Metamodel.load()
    registry_issues = metamodel.validate() + validate_registry(registry, metamodel)
    warnings, verdicts = {}, {}
    report = validate_files(args.paths, registry, entity_resolver=entity_resolver, warnings=warnings, verdicts=verdicts, metamodel=metamodel)
    if registry_issues:
        report = {'<registry>': registry_issues, **report}
    if args.strict:
        # Draft (proposed) records legitimately lack evidence kinds and BIAN anchoring until review;
        # those warnings say so and are not promoted. Everything else is.
        for path, ws in list(warnings.items()):
            hard = [w for w in ws if 'must be supplied before approval' not in w]
            report.setdefault(path, []).extend(hard)
            warnings[path] = [w for w in ws if w not in hard]
    failed = any(report.values())
    if args.json:
        print(json.dumps({'ok': not failed, 'registry_version': registry.get('$schema_version'), 'metamodel_version': metamodel.version,
                          'files': report, 'warnings': warnings, 'verdicts': verdicts}, indent=2))
    else:
        for path, issues in report.items():
            for issue in issues:
                print(f'ERROR: {path}: {issue}')
            for w in warnings.get(path, []):
                print(f'WARNING: {path}: {w}')
            if not issues:
                print(f'OK: {path}' + (' (with warnings)' if warnings.get(path) else ''))
    return EXIT_ISSUES if failed else EXIT_OK


if __name__ == '__main__':
    raise SystemExit(main())
