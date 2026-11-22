"""`sdem data` — the Data Architecture's two commands (docs/design/sdem-data-architecture-spec.md):

- `sdem data lineage <entity>` (DAR-04): where a data entity's data comes from and where it goes — an application that reads entity X and
  writes entity Y gives X → (application) → Y. Derived from approved ACCESSED_BY links with a stated mode, never stored and never
  guessed: a link whose mode is not stated is listed as such.
- `sdem data mode <mapping id> read|write|read_write` (DAR-03): a person states the mode of an access link — ArchiMate 3.2's access types —
  recorded as their decision (GV-01). Only on ACCESSED_BY."""
from pathlib import Path
import argparse, json, sys

from .identity import load as _jload  # DL-11: a design's files read through one boundary (docs/design/sdem-data-layer-spec.md)

MODES = ('read', 'write', 'read_write')
READS, WRITES = {'read', 'read_write'}, {'write', 'read_write'}


def _workspace(ws):
    from .connect import estate_docs
    docs, registry = estate_docs(ws)
    records = {i['id']: i for d in docs.values() for i in d.get('instances', [])}
    return records, registry


def _access(registry):
    """Approved ACCESSED_BY links: (entity, application element, mode or None, mapping id)."""
    return [(m['source']['id'], m['target']['id'], m.get('access_mode'), m['mapping_id']) for m in registry.get('mappings', [])
            if m.get('relationship') == 'ACCESSED_BY' and m.get('status') == 'approved']


def lineage(ws, entity, depth=6):
    """DAR-04: the entity's sources (upstream) and destinations (downstream) through the applications that read and write it."""
    records, registry = _workspace(ws)
    if entity not in records: raise ValueError(f'{entity!r} is not a record in {ws}')
    acc = _access(registry)
    name = lambda i: (records.get(i) or {}).get('name') or i
    def walk(start, up):
        """up: who writes `start`, and what they read; down: who reads `start`, and what they write."""
        out, seen = [], {start}
        frontier = [(start, [start])]
        while frontier:
            e, path = frontier.pop(0)
            if len(path) > depth * 2: continue
            first = {a for d, a, m, _ in acc if d == e and m in (WRITES if up else READS)}
            for app in sorted(first):
                nxt = sorted({d for d, a, m, _ in acc if a == app and d != e and m in (READS if up else WRITES)})
                for d in nxt:
                    out.append({'from': d if up else e, 'through': app, 'to': e if up else d})
                    if d not in seen: seen.add(d); frontier.append((d, path + [app, d]))
        return out
    unstated = [{'entity': d, 'application': a, 'mapping_id': mid} for d, a, m, mid in acc if m is None and d == entity]
    readers = sorted({a for d, a, m, _ in acc if d == entity and m in READS}); writers = sorted({a for d, a, m, _ in acc if d == entity and m in WRITES})
    up, down = walk(entity, True), walk(entity, False)
    return {'entity': entity, 'name': name(entity), 'written_by': writers, 'read_by': readers, 'upstream': up, 'downstream': down,
            'mode_not_stated': unstated, 'names': {i: name(i) for i in {entity, *writers, *readers, *[x[k] for x in up + down for k in ('from', 'through', 'to')], *[u['application'] for u in unstated]}},
            'note': 'derived from approved ACCESSED_BY links with a stated mode (DAR-04) — a link whose mode is not stated is listed, never guessed'}


def gaps(ws):
    """DAR-07: what `sdem status` says about the Data Architecture — only once the design uses it (a domain, an owner or a stated mode), so a
    design that has not started is not flooded. Returns None, or {'no_domain': [...], 'no_owner': [...], 'no_mode': [...]}."""
    records, registry = _workspace(ws)
    typ = lambda i: (records.get(i) or {}).get('type', '')
    at = lambda i: (records.get(i) or {}).get('attributes') or {}
    ents = sorted(i for i in records if typ(i).endswith('.DataEntity') and records[i].get('lifecycle_status') != 'retired')   # either form's name (ST-05)
    doms = [i for i in records if typ(i).endswith('.DataDomain')]
    acc = _access(registry)
    if not (doms or any(at(i).get('data_owner') for i in records) or any(m for _, _, m, _ in acc)): return None
    rels = [r for f in (_jdocs(ws)) for r in f.get('relationships', [])]
    held = {}
    for r in rels:
        if r.get('kind') == 'aggregation' and r.get('source') in doms: held.setdefault(r['target'], []).append(r['source'])
    def owner(i, seen=()):
        if at(i).get('data_owner'): return at(i)['data_owner']
        return next((o for d in held.get(i, []) if d not in seen for o in [owner(d, seen + (d,))] if o), None)
    pii = [e for e in ents if at(e).get('personal_information') is True]
    return {'no_domain': [e for e in ents if e not in held] if doms else [], 'no_owner': [e for e in pii if not owner(e)],
            'no_mode': sorted({mid for d, a, m, mid in acc if d in pii and m is None})}


def _jdocs(ws):
    from .connect import estate_docs
    return list(estate_docs(ws)[0].values())


def set_mode(ws, mapping_id, mode, person, rationale):
    """DAR-03: a person states an access link's mode. Returns (new registry, the link)."""
    if mode not in MODES: raise ValueError(f'mode must be one of {", ".join(MODES)}')
    if not (person or '').strip(): raise ValueError('--person is required — a person states the mode (CTL-21)')
    if not (rationale or '').strip(): raise ValueError('--rationale is required: say in a sentence how you know')
    _, registry = _workspace(ws)
    m = next((x for x in registry.get('mappings', []) if x.get('mapping_id') == mapping_id), None)
    if not m: raise ValueError(f'{mapping_id!r} is not a link in {ws}/mappings.json')
    if m.get('relationship') != 'ACCESSED_BY': raise ValueError(f"{mapping_id} is {m.get('relationship')}: a mode is stated only on ACCESSED_BY (DAR-03)")
    new = json.loads(json.dumps(registry))
    link = next(x for x in new['mappings'] if x.get('mapping_id') == mapping_id)
    link['access_mode'] = mode
    return new, link


def main(argv=None):
    ap = argparse.ArgumentParser(prog='sdem data', description="The Data Architecture: a data entity's lineage, and the mode of an access link (docs/design/sdem-data-architecture-spec.md)",
                                 epilog='examples:\n  sdem data lineage DATA-PAYMENT --workspace work/est\n  sdem data mode MAP-012 write --workspace work/est --person jane.architect --rationale "the hub posts every payment (design §5)"',
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='action', required=True)
    p = sub.add_parser('lineage', help="where a data entity's data comes from and goes — from approved access links with a stated read or write (DAR-04)")
    p.add_argument('entity', help='the data entity, e.g. DATA-PAYMENT'); p.add_argument('--workspace', required=True, metavar='DIR', help='the workspace folder'); p.add_argument('--json', action='store_true', help='the answer as data')
    p = sub.add_parser('mode', help='a person states whether an access link reads, writes or both (DAR-03) — recorded as their decision')
    p.add_argument('mapping_id', help='the ACCESSED_BY link, e.g. MAP-012 (sdem query, or the workbench, shows its id)'); p.add_argument('mode', choices=MODES, help='read, write or read_write — ArchiMate access types')
    p.add_argument('--workspace', required=True, metavar='DIR', help='the workspace folder')
    p.add_argument('--person', required=True, help='your name — a person (CTL-21)'); p.add_argument('--rationale', required=True, help='one sentence: how you know')
    p.add_argument('--dry-run', action='store_true', help='show what would change; write nothing'); p.add_argument('--json', action='store_true', help='the link as data')
    a = ap.parse_args(argv)
    try:
        if a.action == 'lineage':
            r = lineage(a.workspace, a.entity)
            if a.json: print(json.dumps(r, indent=2, ensure_ascii=False)); return 0
            n = r['names'].get
            print(f"{r['name']} ({r['entity']}) — written by {', '.join(map(n, r['written_by'])) or 'nothing stated'}; read by {', '.join(map(n, r['read_by'])) or 'nothing stated'}")
            for k, title in (('upstream', 'comes from'), ('downstream', 'goes to')):
                print(f'  {title}:'); [print(f"    {n(x['from'])} → {n(x['through'])} → {n(x['to'])}") for x in r[k]] or print('    nothing stated')
            if r['mode_not_stated']: print('  mode not stated (sdem data mode …): ' + ', '.join(f"{x['mapping_id']} ({n(x['application'])})" for x in r['mode_not_stated']))
            return 0
        new, link = set_mode(a.workspace, a.mapping_id, a.mode, a.person, a.rationale)
    except ValueError as e:
        print(f'ERROR: {e}', file=sys.stderr); return 1
    if a.json: print(json.dumps(link, indent=2, ensure_ascii=False))
    else: print(f"{'would state' if a.dry_run else 'stated'} {link['mapping_id']}: {link['source']['id']} ACCESSED_BY {link['target']['id']} — {a.mode} ({a.person.strip()})")
    if a.dry_run: return 0
    from .files import write_json
    write_json(Path(a.workspace) / 'mappings.json', new)
    from .governance import record   # GV-01
    record(a.workspace, 'state_access_mode', a.person.strip(), link['mapping_id'], {'mode': a.mode, 'rationale': a.rationale.strip()})
    return 0


if __name__ == '__main__':
    sys.exit(main())
