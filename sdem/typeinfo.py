"""`sdem types` — what you may write, from SDEM's own records (docs/design/sdem-types-search-spec.md, TS-01…TS-06).

  sdem types                      the layers and their kinds of record
  sdem types A1                   each kind of record in A1: its fields (type, required, allowed values) and the links it may have
  sdem types A1.BusinessProcess   one kind in full: definition and source, fields (its own, inherited, common), links inside its
                                  layer, link types to other layers with the evidence each needs, the organisation's rules
  sdem types requirement          the requirements registry's fields, allowed values and condition operators
  sdem types change-set           the change-set format `sdem change propose` takes

With --workspace, the workspace's organisation profile is included (its types, fields, rules, layers, requirement categories).
Read-only. Built because the agent baseline (2026-11-02) found every mistake was a field, value or link no command listed.
"""
import argparse, json, sys

from .paths import DATA_ROOT


def _lifecycle():
    from .conformance import LIFECYCLE   # the values sdem check accepts — one list
    return LIFECYCLE


def _attr(a):
    out = {'name': a['name'], 'type': a['type'], 'required': bool(a.get('required'))}
    if a.get('values'): out['allowed_values'] = a['values']
    if a.get('references'): out['refers_to'] = a['references']
    if a.get('description'): out['description'] = a['description']
    if a.get('status') == 'deprecated':   # LC-13: still accepted, warned — say what replaces it
        out['deprecated'] = True
        loc = (a.get('reference') or {}).get('locator')
        if loc: out['instead'] = loc
    return out


def describe_type(mm, t, full=True):
    from .conformance import definitions, model
    from . import profile as _p
    from .validate import load_registry
    e = mm.entities[t]
    _, common, _ = model()
    defs = definitions(mm, t)
    own = [n for n in defs if n not in common]
    out = {'type': t, 'layer': e['level'], 'abstract': bool(e.get('abstract')), 'extends': mm.ancestors(t), 'definition': e.get('definition', ''),
           'source': ' · '.join(x for x in ((e.get('reference') or {}).get('standard'), (e.get('reference') or {}).get('concept')) if x),
           'identifier': (e.get('identifier') or {}).get('key', ['id']),
           'record_fields': {'required': ['id', 'type', 'version', 'name', 'lifecycle_status'], 'optional': ['description', 'attributes'],
                             'lifecycle_status': list(_lifecycle())},
           'attributes': [_attr(defs[n]) for n in own]}
    cons = mm.relationships['constraints']
    out['links_out'] = sorted({(c['kind'], c['target_type'], c.get('id', '')) for c in cons if c['level'] == e['level'] and mm.is_a(t, c['source_type'])})
    out['links_in'] = sorted({(c['source_type'], c['kind'], c.get('id', '')) for c in cons if c['level'] == e['level'] and mm.is_a(t, c['target_type'])})
    out['links_out'] = [{'kind': k, 'to': x, 'rule': r} for k, x, r in out['links_out']]
    out['links_in'] = [{'from': x, 'kind': k, 'rule': r} for x, k, r in out['links_in']]
    reg = load_registry()['relationships']
    out['link_types_to_other_layers'] = [{'relationship': r['relationship'], 'direction': 'out' if mm.is_a(t, r['source_type']) else 'in',
                                          'other_end': r['target_type'] if mm.is_a(t, r['source_type']) else r['source_type'], 'evidence_needed': r['required_evidence']}
                                         for r in reg if mm.is_a(t, r['source_type']) or mm.is_a(t, r['target_type'])]
    out['organisation_rules'] = [{'id': r['id'], 'message': r.get('message', ''), **{k: r[k] for k in ('when', 'require', 'link', 'compare') if k in r}}
                                 for r in _p.rules() if mm.is_a(t, r['entity'])]
    if full: out['common_attributes'] = sorted(common)
    return out


def requirement_format():
    from . import profile as _p
    from .layers import codes
    s = json.loads((DATA_ROOT / 'schema' / 'requirements.schema.json').read_text(encoding='utf-8'))
    props, req = s['$defs']['requirement']['properties'], s['$defs']['requirement']['required']
    cond = s['$defs']['condition']
    return {'file': 'requirements.json — {"requirements": [...]}; add with sdem requirements propose <file> --workspace DIR --person NAME',
            'set_by_sdem': ['version', 'status', 'history', 'provenance'], 'optional_input': {'source': 'where it came from — kept in provenance'},
            'fields': {k: {'required': k in req, **({'allowed_values': v['enum']} if 'enum' in v else {}), **({'pattern': v['pattern']} if v.get('pattern') else {}),
                           **({'description': v['description']} if v.get('description') else {})} for k, v in props.items()},
            'id': 'REQ- then capitals, digits and dashes, e.g. REQ-GL-AVAIL-01',
            'owner_layer': codes(),
            'category': props['category']['enum'] + _p.requirement_categories(),
            'condition': {'required': cond['required'], 'operator': cond['properties']['operator']['enum'], 'optional': ['unit', 'period'],
                          'example': {'metric': 'availability_pct', 'operator': '>=', 'value': 99.9, 'unit': '%', 'period': 'month'}},
            'subject': 'the id of a record in the workspace (any layer) the requirement is about',
            'derived_from': 'ids of the requirements, or A1 business requirements, it refines',
            'allocated_to': 'ids of lower-layer records that carry part of it',
            'evidence': "list of 'kind:reference' — the document that states it; may be empty when proposed, needed before a person confirms it"}


def change_set_format():
    from .layers import codes
    return {'command': 'sdem change propose <file> --workspace DIR --agent <agent or architect> --person NAME [--dry-run]',
            'shape': {'layer': f"one of {', '.join(codes())} — a change set changes one layer", 'reason': 'one sentence',
                      'changes': [{'op': 'add | update | retire', 'kind': 'for update: modify | rehost | replace | retire (impact); optional',
                                   'record': {'id': '…', 'type': 'e.g. A1.BusinessProcess (sdem types <layer>)', 'version': '1', 'name': '…',
                                              'lifecycle_status': ' | '.join(_lifecycle()), 'description': 'optional', 'attributes': {'…': 'sdem types <type>'}}}],
                      'relationships': {'add': [{'source': 'id', 'kind': 'an allowed kind (sdem types <type>: links_out)', 'target': 'id'}], 'remove': ['…']}},
            'notes': ['update and retire give the full record', 'links between layers are not in a change set — the rules engine proposes them (sdem link) and a person approves (sdem approve)']}


def main(argv=None):
    from .metamodel import Metamodel
    from .layers import layers
    ap = argparse.ArgumentParser(prog='sdem types', formatter_class=argparse.RawDescriptionHelpFormatter,
                                 description='What you may write: each layer\'s kinds of record, their fields (type, required, allowed values) and the links each may have; '
                                             'the requirement and change-set formats. With --workspace, your organisation profile is included.',
                                 epilog='Examples:\n  sdem types A1\n  sdem types A1.BusinessProcess --json\n  sdem types requirement\n  sdem types A3 --workspace workspaces/payments')
    ap.add_argument('what', nargs='?', help='a layer (A1), a type (A1.BusinessProcess), requirement or change-set; nothing: the overview')
    ap.add_argument('--workspace', dest='estate', metavar='DIR', help="include the workspace's organisation profile"); ap.add_argument('--json', action='store_true')
    a = ap.parse_args(argv)
    mm = Metamodel.load(); w = a.what
    if w in ('requirement', 'requirements'): res = requirement_format()
    elif w in ('change-set', 'changeset', 'change_set'): res = change_set_format()
    elif w and '.' in w:
        if w not in mm.entities:
            near = [t for t in mm.entities if w.split('.')[-1].lower() in t.lower()]
            print(f"ERROR: {w!r} is not a type{' — did you mean ' + ', '.join(near[:5]) + '?' if near else ''} (sdem types {w.split('.')[0]} lists them)", file=sys.stderr); return 2
        res = describe_type(mm, w)
    elif w:
        lvl = w.upper()
        if lvl not in [l['code'] for l in layers()]: print(f"ERROR: {w!r} is not a layer, type, 'requirement' or 'change-set' — layers: {', '.join(l['code'] for l in layers())}", file=sys.stderr); return 2
        res = {'layer': lvl, 'types': [describe_type(mm, t, full=False) for t, e in sorted(mm.entities.items()) if e['level'] == lvl and not e.get('artefact')]}
    else:
        res = {'layers': [{'code': l['code'], 'name': l['name'], 'file': l['file'],
                           'types': sorted(t for t, e in mm.entities.items() if e['level'] == l['code'] and not e.get('abstract') and not e.get('artefact'))} for l in layers()],
               'also': ['sdem types requirement', 'sdem types change-set', 'sdem bian search "<words>"']}
    if a.json: print(json.dumps(res, indent=2, ensure_ascii=False)); return 0
    _print(res, w)
    return 0


def _print(res, w):
    if 'layers' in res:
        for l in res['layers']: print(f"{l['code']:<4} {l['name']:<24} {l['file']:<26} {', '.join(t.split('.', 1)[1] for t in l['types'])}")
        print('\nmore: ' + ' · '.join(res['also'])); return
    if 'types' in res:
        for t in res['types']: _print_type(t, brief=True)
        print(f"\nfields every record carries: id, type, version, name, lifecycle_status ({' | '.join(_lifecycle())}); optional description. Full detail: sdem types <type>"); return
    if 'attributes' in res: _print_type(res); return
    if 'condition' in res:   # the requirement format
        print(res['file']); print(f"set by SDEM, never give them: {', '.join(res['set_by_sdem'])}")
        for k, v in res['fields'].items():
            if k in res['set_by_sdem']: continue
            vals = res['category'] if k == 'category' else res['owner_layer'] if k == 'owner_layer' else v.get('allowed_values')
            note = {'id': res['id'], 'subject': res['subject'], 'derived_from': res['derived_from'], 'allocated_to': res['allocated_to'], 'evidence': res['evidence'], 'condition': 'see below'}.get(k, '')
            print(f"  {k:<14} {'REQUIRED' if v['required'] and k != 'evidence' else 'optional':<9} " + (f"one of: {', '.join(vals)}" if vals else note))
        c = res['condition']
        print(f"  condition: metric, operator, value (required); unit, period (optional) — operator one of: {' '.join(c['operator'])}")
        print(f"  example condition: {json.dumps(c['example'])}"); return
    print(json.dumps(res, indent=2, ensure_ascii=False))


def _print_type(t, brief=False):
    print(f"\n{t['type']}" + ('  (abstract — use a subtype)' if t['abstract'] else '') + (f"  extends {' → '.join(t['extends'])}" if t['extends'] else '') + (f"  [{t['source']}]" if t['source'] else ''))
    if not brief and t['definition']: print(f"  {t['definition']}")
    for x in t['attributes']:
        print(f"  {x['name']:<26} {x['type']:<18} {'REQUIRED' if x['required'] else '':<9}" + (f"one of: {', '.join(map(str, x['allowed_values']))}" if x.get('allowed_values') else '')
              + (f"refers to: {', '.join(x['refers_to'])}" if x.get('refers_to') else '')
              + (f"  DEPRECATED — do not use ({x['instead']})" if x.get('deprecated') and x.get('instead') else '  DEPRECATED — do not use' if x.get('deprecated') else ''))
    if t['links_out']: print('  links:     ' + '; '.join(dict.fromkeys(f"{l['kind']} → {l['to'].split('.', 1)[1] if l['to'].count('.') == 1 else l['to']}" for l in t['links_out'])))
    if not brief:
        if t['links_in']: print('  linked by: ' + '; '.join(f"{l['from'].split('.', 1)[1]} {l['kind']}" for l in t['links_in']))
        for r in t['link_types_to_other_layers']: print(f"  to other layers: {r['relationship']} ({r['direction']}) {r['other_end']} — evidence: {', '.join(r['evidence_needed'])}")
        for r in t['organisation_rules']: print(f"  organisation rule {r['id']}: {r['message']}")
        print(f"  also any common field: {', '.join(t['common_attributes'])}")
