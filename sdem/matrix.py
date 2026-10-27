"""`sdem matrix` — business → BIAN → application → technology matrices from approved links (docs/sdem-dashboard-spec.md DB-K01).

The outputs the original design specification lists (§11): capability → service domain, process → service domain,
service domain → application, application → technology, and the end-to-end chain. Only approved links are used.
"""
import argparse, json, sys
from pathlib import Path

PAIRS = [  # (title, relationship(s), source label, target label)
    ('Capability → service domain', ('SUPPORTED_BY',), 'Capability (A1)', 'Service domain (A2)'),
    ('Process → service domain', ('USES_DOMAIN',), 'Process (A1)', 'Service domain (A2)'),
    ('Service domain → application', ('REALIZED_BY',), 'Service domain (A2)', 'Application (A3)'),
    ('Service operation → API', ('IMPLEMENTED_BY',), 'Service operation (A2)', 'API (A3)'),
    ('Application → technology', ('DEPLOYED_ON', 'DEPLOYED_AS'), 'Application (A3)', 'Technology (A4)'),
]


def matrices(fg):
    """{'pairs': [{title, source, target, rows: [{source, source_name, targets: [{id, name, link, relationship}]}]}], 'chain': [...]}"""
    edges = fg.edges(); name = lambda i: (fg.instance(i) or {}).get('name') or i
    out = {'pairs': []}
    for title, rels, sl, tl in PAIRS:
        rows = {}
        for e in edges:
            if e['relationship'] in rels:
                r = rows.setdefault(e['source']['id'], {'source': e['source']['id'], 'source_name': name(e['source']['id']), 'targets': []})
                r['targets'].append({'id': e['target']['id'], 'name': name(e['target']['id']), 'link': e['mapping_id'], 'relationship': e['relationship']})
        out['pairs'].append({'title': title, 'source': sl, 'target': tl, 'rows': sorted(rows.values(), key=lambda r: r['source'])})
    sup = {r['source']: r['targets'] for r in out['pairs'][0]['rows']}
    real = {r['source']: r['targets'] for r in out['pairs'][2]['rows']}
    tech = {r['source']: r['targets'] for r in out['pairs'][4]['rows']}
    chain = []
    for cap, doms in sorted(sup.items()):
        for d in doms:
            apps = real.get(d['id']) or [None]
            for a in apps:
                techs = (tech.get(a['id']) if a else None) or [None]
                for t in techs:
                    chain.append({'capability': cap, 'capability_name': name(cap), 'domain': d['id'], 'domain_name': d['name'],
                                  'application': a['id'] if a else None, 'application_name': a['name'] if a else None,
                                  'technology': t['id'] if t else None, 'technology_name': t['name'] if t else None,
                                  'links': [x for x in (d['link'], a['link'] if a else None, t['link'] if t else None) if x]})
    out['chain'] = chain
    return out


def markdown(m, title='SDEM matrices'):
    lines = [f'# {title}', '', 'From approved links only. Each cell names the record and, in brackets, the approved link.', '',
             '## Capability → service domain → application → technology', '', '| Capability | Service domain | Application | Technology |', '|---|---|---|---|']
    cell = lambda i, n, l=None: f"{n} `{i}`" + (f" ({l})" if l else '') if i else '— *no approved link*'
    for r in m['chain']:
        lk = r['links'] + [None] * 3
        lines.append(f"| {cell(r['capability'], r['capability_name'])} | {cell(r['domain'], r['domain_name'], lk[0])} | {cell(r['application'], r['application_name'], lk[1] if r['application'] else None)} | {cell(r['technology'], r['technology_name'], lk[2] if r['technology'] else None)} |")
    for p in m['pairs']:
        lines += ['', f"## {p['title']}", '', f"| {p['source']} | {p['target']} |", '|---|---|']
        lines += [f"| {r['source_name']} `{r['source']}` | " + '<br>'.join(f"{t['name']} `{t['id']}` ({t['link']}{', ' + t['relationship'] if len(set(x['relationship'] for x in r['targets'])) > 1 else ''})" for t in r['targets']) + ' |' for r in p['rows']]
        if not p['rows']: lines.append('| — | no approved links |')
    return '\n'.join(lines) + '\n'


def main(argv=None):
    ap = argparse.ArgumentParser(prog='sdem matrix', formatter_class=argparse.RawDescriptionHelpFormatter,
                                 description='Business → BIAN → application → technology matrices from approved links.',
                                 epilog='Examples:\n  sdem matrix --estate examples/payment-initiation\n  sdem matrix --estate examples/payment-initiation --md work/matrix.md')
    ap.add_argument('paths', nargs='*', help='architecture datasets and the registry (or --estate / --graph)')
    ap.add_argument('--graph', metavar='DIR'); ap.add_argument('--md', metavar='FILE', help='write Markdown to FILE'); ap.add_argument('--json', action='store_true')
    a = ap.parse_args(argv)
    from .store import GraphReader, StoreError
    try: reader = GraphReader.from_store(a.graph) if a.graph else GraphReader.from_exports(a.paths)
    except (OSError, ValueError, StoreError) as e: print(f'ERROR: {e}', file=sys.stderr); return 2
    m = matrices(reader.fg)
    if a.md: Path(a.md).write_text(markdown(m), encoding='utf-8'); print(f'wrote {a.md}'); return 0
    if a.json: print(json.dumps(m, indent=2, ensure_ascii=False)); return 0
    print('CAPABILITY → SERVICE DOMAIN → APPLICATION → TECHNOLOGY (approved links)')
    for r in m['chain']:
        print(f"  {r['capability_name']} → {r['domain_name']} → {r['application_name'] or '— no approved link'} → {r['technology_name'] or '— no approved link'}   ({', '.join(r['links'])})")
    for p in m['pairs']:
        print(f"\n{p['title'].upper()}")
        for r in p['rows']: print(f"  {r['source_name']} ({r['source']}) → " + '; '.join(f"{t['name']} ({t['id']}, {t['link']})" for t in r['targets']))
        if not p['rows']: print('  — no approved links')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
