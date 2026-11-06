"""`sdem workbench` — one offline HTML page per workspace: the Solution Workspace (Overview, Architecture Designs, Data
Architecture, Knowledge Graphs, Traceability & Impact, Reviews & Changes, Documents & Evidence) and the SDEM Framework
(Overview, Metamodel Explorer, Schemas & Configuration, Relationship Rules, Engine Health) — docs/design/sdem-workbench-ux-spec.md,
UX-N01…N15.

One engine, the page only shows (UX-P01): every fact comes from SDEM's own functions — the dashboard's collect (health,
review, trace, impact, matrices, changes), `sdem document` (UX-D), the metamodel and its rules, the change events' status.
The page's script only selects, filters and navigates. Self-contained: no external file, script or call (UX-P02).
"""
import argparse, json, sys
from pathlib import Path

TEMPLATE = Path(__file__).with_name('workbench.html')
CORE = ('A1', 'A2', 'A3', 'A4')


def _j(p, default=None):
    try: return json.loads(Path(p).read_text(encoding='utf-8'))
    except (OSError, ValueError): return default


def framework():
    """The SDEM Framework side — what the metamodel allows (UX-N08…N12); the same for every workspace."""
    from .metamodel import Metamodel
    from .typeinfo import describe_type
    from .validate import load_registry
    from .dashboard import _controls
    from .document import _label
    from .paths import DATA_ROOT
    mm = Metamodel.load()
    types = []
    for t in mm.entities:
        x = describe_type(mm, t)
        types.append({'type': t, 'label': _label(t), 'layer': x['layer'], 'abstract': x['abstract'], 'extends': x['extends'], 'definition': x['definition'], 'source': x['source'],
                      'attributes': [{k: a.get(k) for k in ('name', 'type', 'required', 'deprecated', 'instead', 'allowed_values', 'refers_to', 'description')} for a in x['attributes']],
                      'links_out': x['links_out'], 'cross': x['link_types_to_other_layers']})
    within = [{k: c.get(k) for k in ('id', 'level', 'source_type', 'kind', 'target_type', 'description', 'basis')} for c in mm.relationships['constraints']]
    cross = [{k: r.get(k) for k in ('mapping_type_id', 'source_type', 'relationship', 'target_type', 'cardinality', 'authority', 'required_evidence', 'direction_semantics')}
             for r in load_registry()['relationships']]
    stab = _j(DATA_ROOT / 'metamodel' / 'stability.json', {}) or {}
    schemas = sorted(p.relative_to(DATA_ROOT).as_posix() for p in (DATA_ROOT / 'schema' / 'entities').rglob('*.json')) if (DATA_ROOT / 'schema' / 'entities').is_dir() else []
    bian = sorted(p.name for p in (DATA_ROOT / 'bian').glob('base-*.json')) if (DATA_ROOT / 'bian').is_dir() else []
    return {'version': mm.version, 'frozen_at': stab.get('frozen_at'), 'frozen_by': stab.get('frozen_by'), 'types': types, 'within': within, 'cross': cross,
            'controls': _controls()['rows'], 'schemas': schemas, 'bian': bian}


def collect(ws, d=None, graph=None, now=None, home=None, fw=None):
    """Everything the page shows for one workspace. `d` (the dashboard's collect) and `fw` (framework()) may be passed in to avoid
    computing them twice (sdem home)."""
    from .dashboard import collect as dash_collect
    from .document import document, to_html, provenance
    from .layers import FILES
    from .agents import Estate, CoordinationError
    ws = Path(ws)
    d = d or dash_collect(ws, graph=graph, now=now)
    present = [l for l in CORE if (ws / FILES[l]).exists()]
    docs, records, rels = {}, [], {}
    for l in CORE:
        if l not in present: rels[l] = []; continue
        doc = document(ws, l)
        body = to_html(doc).split('<body>', 1)[1].rsplit('</body>', 1)[0]
        body = body.split('</h1>', 1)[-1]                     # the page has its own heading
        docs[l] = {'html': body, 'fingerprint': doc['fingerprint'], 'summary': doc['summary'],
                   'gaps': {'no_connection': len(doc['gaps']['no_connection']), 'unconfirmed': len(doc['gaps']['unconfirmed'])}}
        ds = _j(ws / FILES[l], {}) or {}
        records += [{**r, 'layer': l, 'source_text': provenance(r)} for r in ds.get('instances', [])]   # UX-D04's words, for the record panel
        rels[l] = ds.get('relationships', [])
    try: status = {r['id']: r for r in Estate(ws).status()}
    except (CoordinationError, OSError, ValueError): status = {}
    events = [{**e, 'validation': status.get(e['id'], {}).get('validation'), 'planned': status.get(e['id'], {}).get('planned')} for e in d['changes']['events']]
    reqs = (_j(ws / 'requirements.json', {}) or {}).get('requirements', [])
    return {'name': d['name'], 'generated': d['generated'], 'metamodel': d['metamodel'], 'fingerprint': next(iter(docs.values()))['fingerprint'] if docs else '—',
            'home': home, 'present': present, 'missing': [l for l in CORE if l not in present],
            'layers': d['layers'], 'coverage': d['coverage'], 'review': d['review']['rows'], 'trace': d['records'], 'kinds': d['kinds'],
            'matrix': d['matrix'], 'changes': {**d['changes'], 'events': events}, 'docs': docs, 'records': records, 'rels': rels,
            'registry': (_j(ws / 'mappings.json', {}) or {}).get('mappings', []),
            'reqs': [{k: q.get(k) for k in ('id', 'name', 'status', 'category', 'subject', 'allocated_to', 'condition')} for q in reqs],
            'stale': d['stale'], 'checks': _checks(d), 'diagrams': _diagrams(ws), 'graph_state': _graph_state(ws, graph), 'profile': (ws / 'sdem-profile.json').exists(), 'framework': fw or framework()}


def _diagrams(ws):
    """DG-13: every template's drawing for this workspace (the page only shows them)."""
    from . import viewpoints
    D = viewpoints.Data(ws); out = {}
    if not D.present: return out
    for t in viewpoints.templates()['templates']:
        if t['layer'] != 'all' and t['layer'] not in D.present: continue
        x = viewpoints.build(D, t['id'])
        out[t['id']] = {'template': t['id'], 'code': x['code'], 'name': x['name'], 'viewpoint': x['viewpoint'], 'layer': x['layer'], 'svg': x['svg'],
                        'notes': x['notes'], 'elements': len(x['elements']), 'lines': len(x['lines'])}
    return out


def _checks(d):
    """`sdem check`'s errors and advice as the dashboard collected them, each message once with the datasets it is reported for
    (a metamodel mismatch is reported by every dataset; the page shows it once)."""
    out = []
    for level, key in (('error', 'errors'), ('advice', 'advice')):
        seen = {}
        for where, msgs in [(l['level'], l.get(key, [])) for l in d['layers']] + [('mappings.json', d.get('registry', {}).get(key, []) or [])]:
            for m in msgs:
                norm = m.replace('document metamodel_version', 'metamodel_version')
                norm = norm.split(' — move the workspace with')[0]
                seen.setdefault(norm, []).append(where)
        out += [{'level': level, 'text': t, 'where': w} for t, w in seen.items()]
    return out


def _graph_state(ws, graph=None):
    """NV-03's state of the workspace's graph store — current, stale, missing or blocked — with its reason and fixing command."""
    from .nav import graph_state, default_store
    try:
        g = graph_state(ws, graph or default_store(ws))
        return {'state': g.get('state'), 'reason': g.get('reason'), 'command': g.get('command')}
    except Exception as e:   # the page still shows everything else
        return {'state': 'unknown', 'reason': str(e), 'command': None}


def render(data):
    from .viewpoints import SCRIPT
    return TEMPLATE.read_text(encoding='utf-8').replace('/*DIAGRAM_SCRIPT*/', SCRIPT).replace('/*DATA*/null', json.dumps(data, ensure_ascii=False).replace('</', '<\\/'))


def write(ws, out, **kw):
    out = Path(out); out.parent.mkdir(parents=True, exist_ok=True)
    data = collect(ws, **kw)
    out.write_text(render(data), encoding='utf-8')
    return out, data


def main(argv=None):
    ap = argparse.ArgumentParser(prog='sdem workbench', formatter_class=argparse.RawDescriptionHelpFormatter,
                                 description='Write the workbench for one workspace: one offline page with the Solution Workspace (designs as documents, '
                                             'tables by type and diagrams; datasets; the knowledge graph; trace and impact; reviews and changes; documents and evidence) '
                                             'and the SDEM Framework (metamodel, schemas and configuration, relationship rules, engine health). Read-only.',
                                 epilog='Examples:\n  sdem workbench --workspace examples/payment-initiation -o work/workbench.html\n'
                                        '  sdem home -o work/sdem     # every workspace, each with its workbench')
    ap.add_argument('--workspace', required=True, metavar='DIR')
    ap.add_argument('-o', '--out', default='work/workbench.html', metavar='FILE', help='the page to write (default work/workbench.html)')
    ap.add_argument('--json', action='store_true', help='print a summary of what the page shows (the page is written too)')
    a = ap.parse_args(argv)
    ws = Path(a.workspace)
    if not (ws / 'mappings.json').exists() and not any((ws / f).exists() for f in ('a1-business.json', 'a2-service-domain.json', 'a3-application.json', 'a4-technology.json')):
        print(f'ERROR: {ws}: not a workspace (no layer files, no mappings.json) — sdem new --workspace {ws} --person <you> starts one', file=sys.stderr); return 2
    out, data = write(ws, a.out)
    if a.json:
        print(json.dumps({'page': str(out), 'workspace': data['name'], 'layers': data['present'], 'missing_layers': data['missing'],
                          'records': len(data['records']), 'proposals': len(data['review']), 'change_events': len(data['changes']['events']),
                          'framework': {'metamodel': data['framework']['version'], 'types': len(data['framework']['types']),
                                        'rules_inside_layers': len(data['framework']['within']), 'relationships_between_layers': len(data['framework']['cross'])}},
                         indent=2, ensure_ascii=False)); return 0
    print(f"wrote {out} — {data['name']}: {len(data['records'])} records in {', '.join(data['present']) or 'no layer'}; "
          f"{len(data['review'])} proposal(s), {len(data['changes']['events'])} change event(s)" + (f"; missing layers: {', '.join(data['missing'])}" if data['missing'] else ''))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
