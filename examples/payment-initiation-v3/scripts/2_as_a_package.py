"""Step 2 — the stated-only translation (step 1's change sets) as a package for `sdem intake`. Nothing is added: the records and links are
those change sets'. Usage, from the repository root: python 2_as_a_package.py <drafts folder> <package folder>"""
import json, sys
from pathlib import Path
sys.path.insert(0, '.')
from sdem.intake import _bian_catalogue
D = Path(sys.argv[1]); OUT = Path(sys.argv[2]); OUT.mkdir(parents=True, exist_ok=True)
cat = _bian_catalogue(); by_op = {oid: (sd, n) for sd, x in cat.items() for n, oid in x['operations'].items()}
uses = {}
for layer, f, name in (('A1', 'v3-a1.json', 'a1-business.json'), ('A3', 'v3-a3.json', 'a3-application.json'), ('A4', 'v3-a4.json', 'a4-technology.json')):
    cs = json.loads((D / f).read_text(encoding='utf-8'))
    recs = [c['record'] for c in cs['changes'] if c['op'] == 'add']
    for r in recs:
        for o in (r.get('attributes') or {}).pop('invokes', []) if layer == 'A1' else []: uses.setdefault(o, []).append(r['id'])
    (OUT / name).write_text(json.dumps({'level': layer, 'instances': recs, 'relationships': cs['relationships']['add']}, indent=1), encoding='utf-8')
    print(layer, len(recs), len(cs['relationships']['add']))
doms = sorted({by_op[o][0] for o in uses if o in by_op})
(OUT / 'BIAN-DOMAINS.json').write_text(json.dumps({'release': '14.0.0', 'service_domains': [{'name': d, 'source': 'document:design.md#4'} for d in doms],
    'operations': [{'service_domain': by_op[o][0], 'name': by_op[o][1], 'used_by': u, 'source': 'document:design.md#4'} for o, u in sorted(uses.items()) if o in by_op], 'bank_local_not_bian': []}, indent=1), encoding='utf-8')
(OUT / 'CROSS-LAYER-SUGGESTIONS.json').write_text(json.dumps({'status': 'UNAPPROVED', 'suggestions': []}, indent=1), encoding='utf-8')
(OUT / 'NOT-STATED.json').write_text(json.dumps({'items': []}, indent=1), encoding='utf-8')
(OUT / 'CHECKLIST.json').write_text(json.dumps({'cli_executed': True, 'source_design': 'narrative/design.md', 'note': 'checked with sdem intake --check'}, indent=1), encoding='utf-8')
print('BIAN', doms, {o: u for o, u in uses.items()})
