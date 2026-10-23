"""One confidence rule for every layer of the model, derived from each item's source reference, its verification,
and whether it was validated against sealed answers in the use-case runs.

  high   — defined by a public standard and checked (BIAN public material, OpenAPI, or a standard concept or
           relationship confirmed by the open-source Archi oracle); or an SDEM data-contract field, which SDEM defines
           authoritatively.
  medium — built on a standard concept or relationship as SDEM chose to model it; or BIAN intent / target only;
           or an SDEM definition, a login-gated source, or a cited-but-unverified source that was validated against
           sealed answers; or institution data under an SDEM convention.
  low    — no standard basis and not validated against sealed answers; or deprecated.

`python -m sdem.confidence` reapplies the rule to the records and reports every change; `--check` fails if any record
disagrees with the rule.
"""
from pathlib import Path
import argparse, glob, json, re
from collections import Counter
from sdem.metamodel import MM_DIR

ROOT = MM_DIR.parent
RULE = __doc__.split('\n\n')[1].strip()


def validated_rules():
    """Plan IDs with at least one hit against sealed answers in the inference logs."""
    hits = Counter()
    for f in glob.glob(str(ROOT / 'examples' / '*' / '*inference-log.json')):
        d = json.loads(Path(f).read_text(encoding='utf-8'))
        for a in d.get('attempts') or d.get('inferences') or []:
            m = re.match(r'S\d+|B\d+', str(a.get('plan_id') or ''))
            if m and a.get('outcome') == 'hit': hits[m.group(0)] += 1
    return {k for k, v in hits.items() if v}


def _j(p): return json.loads(Path(p).read_text(encoding='utf-8'))


def entity(e, val, rules_by_entity):
    ds = e['definition_source']; tested = bool(rules_by_entity.get(e['type'], set()) & val)
    if ds in ('bian_reference', 'archimate_native'):
        return 'high', 'concept defined by a public standard and checked (BIAN public portal / Archi oracle)'
    if ds == 'togaf_informed':
        return ('medium', 'login-gated TOGAF source, unverified; validated against sealed answers') if tested else ('low', 'login-gated TOGAF source, unverified; not validated')
    if ds in ('bian_aligned', 'archimate_aligned') or (ds == 'sdem_extension' and e['alignment_kind'] in ('specialization', 'conceptual', 'related')):
        return 'medium', 'built on a standard concept as SDEM chose to model it'
    return ('medium', 'SDEM definition with no standard concept; validated against sealed answers') if tested else ('low', 'SDEM definition with no standard concept; not validated')


def attribute(a, val):
    rs = set(re.findall(r'S\d+', a.get('read_by', ''))); tested = bool(rs & val)
    if a['status'] == 'deprecated': return 'low', 'deprecated'
    src = a['source']
    if src in ('BIAN', 'OpenAPI'):
        if a['entity'] == 'A3.APIOperation' and a['name'] == 'payload_fields':
            return 'medium', 'OpenAPI defines payload schemas; SDEM flattens them to field names'
        return 'high', f'defined by a public standard ({src}) and checked'
    if src == 'ArchiMate relationship': return 'medium', 'standard relationship (confirmed by the Archi oracle) recorded on the entity as SDEM chose'
    if src == 'institution': return 'medium', 'institution data under an SDEM convention'
    if src == 'TOGAF': return ('medium', 'login-gated TOGAF source; validated against sealed answers') if tested else ('low', 'login-gated TOGAF source; not validated')
    if a['entity'] in ('A4.Deployment',) or a['entity'] == 'A3.DataEntity' and a['name'] == 'attributes' or a['name'] in ('lifecycle_states', 'deployed_as'):
        return 'medium', 'SDEM field built on a standard concept'
    return ('medium', 'SDEM field with no standard concept; validated against sealed answers') if tested else ('low', 'SDEM field with no standard concept; not validated')


def within(c, val):
    v = c['verification']
    if v in ('verified', 'verified_against_archi'): return 'high', 'standard relationship checked (BIAN public material / Archi oracle)'
    if v == 'sdem_definition': return 'medium', 'follows from an SDEM extension entity built on a standard concept'
    if v == 'unverified_togaf': return 'medium', 'login-gated TOGAF source, unverified; exercised by the C3 coverage case'
    return 'low', 'SDEM reading with no standard relationship; not validated'


def rel_type(x, val, row):
    v = x.get('verification'); tested = row in val
    if v == 'verified': return 'high', 'BIAN public guidance names this alignment and it was checked'
    if v == 'verified_intent_or_target_only': return 'medium', 'BIAN states the intent or the target only'
    if tested: return 'medium', ('cited source login-gated and unverified' if v and v.startswith('unverified') else 'SDEM definition') + '; validated against sealed answers'
    return 'low', 'no standard basis; not validated'


def rule(m, val, verification):
    d = m['rule_decision']
    if d == 'bian_internal': return 'high', 'BIAN-internal structure, checked against the public portal'
    if d in ('not_a_mapping', 'historical_method', 'subsumed', 'not_encodable'): return 'n/a', f"not used ({d.replace('_', ' ')})"
    if verification == 'verified': return 'high', 'official guidance, checked'
    if verification == 'verified_intent_or_target_only': return 'medium', 'BIAN states the intent or the target only'
    if m['id'] in val: return 'medium', ('cited source unverified' if verification.startswith('unverified') else 'no official source; SDEM rule') + '; validated against sealed answers'
    return 'low', 'no official source; not validated'


def apply(write=True):
    val = validated_rules(); changes = []
    rules = _j(MM_DIR / 'relationship-rules.json'); off = {m['id']: m for m in _j(MM_DIR / 'official-mappings.json')['mappings']}
    by_entity = {}
    for m in rules['mappings']:
        for t in (m['source'], m['target']): by_entity.setdefault(t, set()).add(m['id'])
    def setc(obj, key, new, basis, label, bkey='confidence_basis'):
        if obj.get(key) != new: changes.append((label, obj.get(key), new, basis))
        obj[key] = new; obj[bkey] = basis
    for f in sorted(glob.glob(str(MM_DIR / 'a[1-4]-*.json'))):
        d = _j(f)
        for e in d['entities']:
            c, b = entity(e, val, by_entity); setc(e, 'confidence', c, b, e['type'])
        if write: Path(f).write_text(json.dumps(d, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    at = _j(MM_DIR / 'entity-attributes.json')
    for a in at['attributes']:
        c, b = attribute(a, val); setc(a, 'confidence', c, b, f"{a['id']} {a['entity']}.{a['name']}")
    for cf in at['core_fields']:
        c, b = ('high', 'BIAN concept identifier') if cf['name'] == 'canonical_id' else ('high', 'SDEM data-contract field, defined authoritatively by SDEM')
        setc(cf, 'confidence', c, b, f"core {cf['name']}")
    at['confidence_rule'] = RULE
    if write: (MM_DIR / 'entity-attributes.json').write_text(json.dumps(at, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    lr = _j(MM_DIR / 'level-relationships.json')
    for c in lr['constraints']:
        cc, b = within(c, val); setc(c, 'confidence', cc, b, c['id'])
    if write: (MM_DIR / 'level-relationships.json').write_text(json.dumps(lr, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    reg = _j(ROOT / 'schema' / 'relationship-types.json')
    for x in reg['relationships']:
        row = re.match(r'plan row (S\d+)', x.get('source_reference', '')).group(1)
        c, b = rel_type(x, val, row); setc(x, 'confidence', c, b, x['mapping_type_id'])
    if write: (ROOT / 'schema' / 'relationship-types.json').write_text(json.dumps(reg, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    for m in rules['mappings']:
        c, b = rule(m, val, off[m['id']]['verification']); setc(m, 'basis_confidence', c, b, f"rule {m['id']}", 'basis_confidence_reason')
    if write: (MM_DIR / 'relationship-rules.json').write_text(json.dumps(rules, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    return changes


def main(argv=None):
    ap = argparse.ArgumentParser(prog='sdem-confidence', description='Apply the single confidence rule to every layer of the model.')
    ap.add_argument('--check', action='store_true')
    args = ap.parse_args(argv)
    ch = apply(write=not args.check)
    for label, old, new, basis in ch: print(f"{label}: {old} -> {new}  ({basis})")
    if args.check:
        print('consistent' if not ch else f'{len(ch)} record(s) disagree with the rule'); return 0 if not ch else 1
    print(f'{len(ch)} change(s) applied'); return 0


if __name__ == '__main__':
    raise SystemExit(main())
