"""`sdem home` — the main dashboard: SDEM itself (the metamodel, its relationships, configuration and health) and every
project (estate) in use, each with its own dashboard (docs/sdem-dashboard-design.md §8, spec DB-H*).

Writes a small offline site: <out>/index.html (home) and <out>/projects/<name>.html (one `sdem dashboard` per estate, with a
link back home). Everything is computed here with SDEM's own functions — the generated-file checks and the engine's
acceptance cases run live at generation — and the pages only display it. No server, no network, no AI.
"""
import argparse, contextlib, datetime, glob, html, io, json, re, sys
from pathlib import Path

from .metamodel import Metamodel

ROOT = Path(__file__).resolve().parents[1]
LEVELS = {'A1': 'A1 Business', 'A2': 'A2 Service domain (BIAN)', 'A3': 'A3 Application', 'A4': 'A4 Technology'}
DATASETS = ('a1-business.json', 'a2-service-domain.json', 'a3-application.json', 'a4-technology.json')
BOX_W, BOX_H, STEP_X, STEP_Y, PER_ROW, PAD = 196, 36, 210, 50, 6, 20


def _j(p): return json.loads(Path(p).read_text(encoding='utf-8'))


def find_estates(roots=(), estates=()):
    """Estate folders: given ones, plus every sub-folder of a root that has mappings.json and at least one dataset."""
    out = []
    for e in estates:
        out.append(Path(e))
    for r in roots:
        for d in sorted(Path(r).iterdir()):
            if d.is_dir() and (d / 'mappings.json').exists() and any((d / f).exists() for f in DATASETS): out.append(d)
    seen, uniq = set(), []
    for e in out:
        k = e.resolve()
        if k not in seen: seen.add(k); uniq.append(e)
    return uniq


def metamodel():
    mm = Metamodel.load()
    ents = [e for f in sorted(glob.glob(str(ROOT / 'metamodel' / 'a[1-4]-*.json'))) for e in _j(f)['entities']]
    attrs = _j(ROOT / 'metamodel' / 'entity-attributes.json')
    lr = _j(ROOT / 'metamodel' / 'level-relationships.json')
    types = _j(ROOT / 'schema' / 'relationship-types.json')['relationships']
    rules = _j(ROOT / 'metamodel' / 'relationship-rules.json')
    by_entity = {}
    for a in attrs['attributes']:
        if a.get('status') == 'active': by_entity.setdefault(a['entity'], []).append({'name': a['name'], 'type': a['type'], 'required': a.get('required', False), 'description': a.get('description', '')})
    entities = []
    for e in ents:
        t = e['type']
        own = by_entity.get(t, [])
        inherited = [x for anc in mm.ancestors(t) for x in by_entity.get(anc, [])]
        ref = e.get('reference') or {}
        entities.append({'type': t, 'level': e['level'], 'abstract': e.get('abstract', False), 'artefact': e.get('artefact', False), 'extends': e.get('extends'),
                         'definition': e.get('definition', ''), 'standard': ref.get('standard', ''), 'concept': ref.get('concept', ''), 'locator': ref.get('locator', ''),
                         'evidence_status': e.get('evidence_status', ''), 'definition_source': e.get('definition_source', ''), 'reasoning': e.get('reasoning', ''),
                         'attributes': own, 'inherited': inherited,
                         'within': [c['id'] for c in lr['constraints'] if mm.is_a(t, c['source_type']) or mm.is_a(t, c['target_type'])],
                         'cross': [x['relationship'] + ' ' + ('→ ' + x['target_type'] if mm.is_a(t, x['source_type']) else '← ' + x['source_type']) for x in types if mm.is_a(t, x['source_type']) or mm.is_a(t, x['target_type'])],
                         'rules': sorted({m['id'] for m in rules['mappings'] if t in (m.get('source'), m.get('target')) or any(mm.is_a(t, s) for s in (m.get('source'), m.get('target')) if s and s.startswith('A'))})})
    within = [{'id': c['id'], 'level': c['level'], 'source': c['source_type'], 'kind': c['kind'], 'target': c['target_type'], 'official': c.get('official_id'),
               'basis': c.get('basis', ''), 'description': c.get('description', '')} for c in lr['constraints']]
    cross = [{'relationship': x['relationship'], 'source': x['source_type'], 'target': x['target_type'], 'cardinality': x['cardinality'], 'authority': x['authority'],
              'evidence': x['required_evidence'], 'verification': x.get('verification', ''), 'confidence': x.get('confidence', ''), 'meaning': x.get('direction_semantics', ''),
              'source_reference': x.get('source_reference', '')} for x in types]
    rrows = [{'id': m['id'], 'source': m.get('source'), 'relation': m.get('relation'), 'target': m.get('target'), 'step': m.get('fill_step'), 'decision': m.get('rule_decision'),
              'confidence': m.get('confidence'), 'source_reference': m.get('source_reference', ''), 'reasoning': m.get('reasoning', '')} for m in rules['mappings']]
    return {'version': mm.version, 'entities': entities, 'within': within, 'kinds': lr.get('kinds'), 'cross': cross, 'rules': rrows,
            'steps': rules['steps'], 'decisions': rules['rule_decisions'], 'common_attributes': attrs.get('common_attributes', []),
            'core_fields': attrs.get('core_fields', []), 'derived_attributes': attrs.get('derived_attributes', [])}


def layout(entities, cross):
    """Positions for the metamodel picture: four bands, entity types wrapped PER_ROW, cross-level relationship types as edges."""
    nodes, bands, y = [], [], PAD
    for lvl, title in LEVELS.items():
        es = [e for e in entities if e['level'] == lvl and not e['artefact']]
        es.sort(key=lambda e: (e['abstract'], e['type']))
        rows = (len(es) + PER_ROW - 1) // PER_ROW; top = y
        for n, e in enumerate(es):
            nodes.append({'type': e['type'], 'level': lvl, 'abstract': e['abstract'], 'x': PAD + 110 + (n % PER_ROW) * STEP_X, 'y': y + 28 + (n // PER_ROW) * STEP_Y})
        h = 28 + rows * STEP_Y; bands.append({'level': lvl, 'title': title, 'y': top, 'h': h}); y += h + 26
    pos = {n['type']: n for n in nodes}
    edges = [{'s': x['source'], 't': x['target'], 'rel': x['relationship']} for x in cross if x['source'] in pos and x['target'] in pos]
    return {'nodes': nodes, 'bands': bands, 'edges': edges, 'width': PAD * 2 + 110 + PER_ROW * STEP_X, 'height': y, 'box': [BOX_W, BOX_H]}


def health(mm_data):
    from .cli import GENERATORS
    from . import acceptance
    from .inference import ENGINES
    gens = []
    for g in GENERATORS:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(io.StringIO()):
            mod = __import__(f'sdem.{g}', fromlist=['main']); code = mod.main(['--check'])
        gens.append({'name': g, 'current': code == 0})
    rows = acceptance.run(ENGINES['rules']())
    acc = [{'case': r['case'], 'estate': r['estate'], 'passed': r['passed'], 'precision': round(r['score']['registry']['precision'], 2), 'recall': round(r['score']['registry']['recall'], 2),
            'floor_precision': round(r['floor']['registry']['precision'], 2), 'floor_recall': round(r['floor']['registry']['recall'], 2)} for r in rows]
    ctl = _j(ROOT / 'metamodel' / 'controls.json')
    gaps = _j(ROOT / 'metamodel' / 'metamodel-spec-gaps.json')['gaps']
    from .dashboard import _controls
    entities = mm_data['entities']
    ev = {}
    for e in entities: ev[e['evidence_status']] = ev.get(e['evidence_status'], 0) + 1
    return {'generators': gens, 'acceptance': acc, 'controls': _controls(), 'built_controls': sum(1 for c in ctl['controls'] if c.get('status', 'built') == 'built'),
            'controls_total': len(ctl['controls']), 'control_gaps': ctl['gaps'],
            'spec_gaps': [{'id': g['id'], 'kind': g['kind'], 'implemented': g['implemented'], 'status': g['status']} for g in gaps],
            'evidence_status': ev}


def config():
    from .diff import ALLOWED_TRANSITIONS
    from .rules_engine import BAND
    ir = _j(ROOT / 'schema' / 'impact-rules.json')
    ea = _j(ROOT / 'metamodel' / 'entity-attributes.json')
    return {'impact': {'classes': ir['classes'], 'kinds': ir['kinds'], 'supersede_for': ir['supersede_mappings_touching_changed_instance_for'], 'version': ir.get('$schema_version')},
            'transitions': {k: sorted(v) for k, v in ALLOWED_TRANSITIONS.items()}, 'bands': BAND, 'confidence_rule': ea.get('confidence_rule'),
            'agents': {'layer agents': ['sdem-a1-business', 'sdem-a2-bian', 'sdem-a3-application', 'sdem-a4-technology'], 'orchestrator': 'sdem-orchestrator'},
            'files': [{'file': f, 'holds': h} for f, h in (
                ('metamodel/a1-business.json … a4-technology.json', 'entity types per architecture'), ('metamodel/level-relationships.json', 'links allowed inside an architecture'),
                ('schema/relationship-types.json', 'the link types allowed between architectures'), ('metamodel/relationship-rules.json', "the rules engine's rules"),
                ('metamodel/entity-attributes.json', 'attributes per entity type'), ('schema/impact-rules.json', 'how a change is classified'),
                ('metamodel/controls.json', 'the controls and gaps'), ('metamodel/metamodel-spec-gaps.json', 'differences from the high-level spec, and decisions'))]}


def _wrap(text, n):
    """At most two lines of about n characters, split at words."""
    words, lines = text.split(), ['']
    for w in words:
        if lines[-1] and len(lines[-1]) + 1 + len(w) > n and len(lines) < 2: lines.append(w)
        else: lines[-1] = (lines[-1] + ' ' + w).strip()
    return lines


def _ex(n):
    p = ROOT / 'docs' / 'evidence' / f'use-case-example-{n}' / 'results.json'
    return _j(p) if p.exists() else None


def components(m, h, projects):
    """The SDEM component architecture (the original design's logical architecture, docs/BIAN_SDEM_Design_Specification.md §2.1,
    plus the planning lane AID, change coordination and the workbench): boxes, status, live figures, details; and the flows."""
    recs = {l: sum(p['layers'].get(l, 0) for p in projects) for l in LEVELS}
    ents = {l: sum(1 for e in m['entities'] if e['level'] == l and not e['artefact']) for l in LEVELS}
    within = {l: sum(1 for w in m['within'] if w['level'] == l) for l in LEVELS}
    links = sum(p['links'] for p in projects); approved = sum(p['by_status'].get('approved', 0) for p in projects)
    acc = h['acceptance']; acc_ok = sum(a['passed'] for a in acc)
    ex2, ex3 = _ex(2), _ex(3)
    e2 = (sum(ok for x in ex2['runs'] for _, ok in x['checks']), sum(len(x['checks']) for x in ex2['runs']), sum(s_['pass'] for s_ in ex2['safety']), len(ex2['safety'])) if ex2 else None
    e3 = (sum(c['pass'] for c in ex3['criteria']), len(ex3['criteria']), sum(c['pass'] for c in ex3['controls_tests']), len(ex3['controls_tests'])) if ex3 else None
    W, H = 236, 72
    C = []
    def add(cid, title, sub, status, x, y, what, where, figures, nxt, tabs=(), w=W, hh=H):
        C.append({'id': cid, 'title': title, 'lines': _wrap(title, 26), 'sub': sub, 'status': status, 'x': x, 'y': y, 'w': w, 'h': hh, 'what': what, 'where': where, 'figures': figures, 'next': nxt, 'tabs': list(tabs)})
    add('workbench', 'SDEM Workbench', 'VS Code · CLI · dashboards · Copilot', 'built', 994, 20,
        'How architects use SDEM: the project open in VS Code, SDEM run from the terminal (the CLI is its only interface), the dashboards for an overview, GitHub Copilot Chat for optional AI support. Every function works without AI.',
        ['sdem --help (every journey)', 'sdem home · sdem dashboard', 'docs/sdem-workbench-user-guide.md', '.github/ — Copilot instructions, agents, prompts, skills'],
        [f"{len(projects)} project(s) in use", 'no MCP, no AI API inside SDEM'], 'Phase 2 dashboard (sdem serve, actions and forms) — proposed', ['projects', 'config'])
    add('bian', 'BIAN Reference Architecture Repository', 'domains · operations · business objects', 'partial', 517, 20,
        'The BIAN service landscape SDEM anchors to: every A2 element and every BIAN identity comes from here, never invented (CTL-17).',
        ['each estate\'s a2-service-domain.json (synthetic, made-up BIAN content)', 'the AID test catalogue (merged by BIAN canonical id)'],
        [f"{ents['A2']} BIAN entity types in the metamodel", f"{recs['A2']} A2 records across the projects"], 'A licensed BIAN catalogue with real BIAN ids — roadmap v0.15', ['entities'])
    add('history', 'Historical Design Repository', 'past designs · decisions · baselines', 'partial', 40, 20,
        'Earlier designs, diagrams and decisions kept unchanged and referenceable beside new BIAN-aligned designs (original design §9, acceptance criteria 6 and 10). Built: sdem history reads a Confluence HTML export with rules (no AI) — tables, draw.io diagrams and known names in the text — into candidate records with their source, plus an index of every design; pasted pictures go to a person.',
        ['sdem history inspect · sdem history extract', 'metamodel/history-rules.json (tune without code)', 'docs/sdem-history-design.md', 'graph store baselines (sdem baseline)'],
        ['tested on a synthetic Confluence export (tests/fixtures/confluence-export-sample)', 'candidates never above medium confidence'], 'Run it on the real export (work machine); past-baseline views — roadmap v0.16')
    add('metamodel', 'SDEM Mapping Metamodel & Rules', 'the rulebook', 'built', 40, 160,
        'What may exist in each architecture, how records may be linked inside and between the architectures, and the rules the engine applies — each with its published source, reasoning and confidence.',
        ['metamodel/ (entity types, links inside, rules, attributes)', 'schema/relationship-types.json (links between)', 'docs/architecture-metamodel-detail-level-spec.md (governing)'],
        [f"{len(m['entities'])} entity types", f"{len(m['within'])} links allowed inside", f"{len(m['cross'])} link types between", f"{len(m['rules'])} engine rules",
         f"generated documents {'current' if all(g['current'] for g in h['generators']) else 'STALE'}"], 'Rulebook finding G-A-1 (rule S44 step) — owner decision', ['entities', 'within', 'cross', 'rules', 'entitymap'])
    add('engine', 'SDEM Mapping Engine', 'process · information · architecture', 'built', 517, 160,
        'Proposes the links between the architectures by applying the rulebook to the data — rules, not AI — each proposal with rule, reasoning and confidence. Proposals only; a person approves.',
        ['sdem link · sdem review · sdem explain', 'sdem/rules_engine.py', 'acceptance: sdem model accept'],
        [f"{acc_ok} of {len(acc)} acceptance cases pass (run now)", 'CTL-22: engine checked against the rulebook'], 'A blind test case written by someone else', ['rules', 'health'])
    add('aid', 'Architecture Inference Design (AID)', 'planning lane — projects missing layers', 'built', 994, 160,
        'Projects the architecture layers you do not have from the ones you do — forward (business → technology) or reverse — as a projected design with inference confidence, for planning; then compares it with the real design (gap analysis).',
        ['sdem aid project · check · gaps', 'sdem view --projection', 'docs/aid-design.md'],
        ([f"use-case example 2: {e2[0]} of {e2[1]} expectations, safety {e2[2]} of {e2[3]}"] if e2 else []) + ['never above medium confidence; name-only evidence low'],
        'AI suggestions through Copilot (AID-D08) — owner decision', ['health'])
    add('validation', 'SDEM Validation & Approval', 'checks · controls · a person approves', 'built', 40, 300,
        'Every dataset, link and change is checked against the rulebook before it is trusted — including BIAN identity: a BIAN-anchored link needs its BIAN release and canonical id from the reference repository. A person approves each link with the evidence its type needs, in a reviewed pull request.',
        ['sdem check · sdem validate · sdem approve', 'metamodel/controls.json — the controls register', 'CI on every push'],
        [f"{h['built_controls']} controls built", f"{len(h['control_gaps'])} known gaps (G-A partly closed)"], 'Phase 2: approve from the dashboard (sdem serve) — proposed', ['health'])
    add('projections', 'Projection packages', 'PRJ- · planned, never real data', 'built', 994, 300,
        'AID\'s projected designs, kept apart from real data: CTL-16 rejects them in datasets, the registry and graph stores; CTL-17 requires their provenance and caps their confidence.',
        ['<folder>/projection.json, projected-*.json, projected-links.json', 'schema/projection.schema.json'],
        ['CTL-16 · CTL-17 tested both ways'], '—', ['health'])
    add('coordination', 'Change coordination & agents', 'change sets · events · work items', 'built', 756, 440,
        'Changes to an architecture as checked, one-layer change sets; their impact recorded as change events; work items for the other layers. Optional Copilot agents — one per architecture and an orchestrator — work through the same records.',
        ['sdem change propose · adopt · revert', 'sdem events · sdem work', '.github/agents/ (5 agents)', '<estate>/coordination/'],
        ([f"use-case example 3: {e3[0]} of {e3[1]} criteria, controls {e3[2]} of {e3[3]}"] if e3 else []) + ['CTL-19 ownership · CTL-20 provenance (incl. direct edits) · CTL-21 a person approves'],
        'Run the spike in VS Code; then score the real agents (AG-E01)', ['health'])
    add('kg', 'Federated Knowledge Graph', 'cross-layer mapping registry & traceability', 'built', 278, 440,
        'The approved links between the architectures (the Relationship Registry) joined with the four architecture graphs: trace any record up or down, classify the impact of a change, build matrices.',
        ['<estate>/mappings.json (the registry)', 'sdem build → graph store', 'sdem trace · sdem impact · sdem matrix · sdem view'],
        [f"{approved} approved links of {links} across the projects"], 'Ingestion of real designs (v0.11); an enterprise-wide graph across projects', ['projects'])
    for n, (lvl, title) in enumerate(LEVELS.items()):
        add(lvl.lower(), f"{lvl} {title.split(' ', 1)[1]} Graph & Schema", 'independently governed', 'built', 40 + n * 306, 620,
            f"The {title} architecture: its own records and the links inside it, checked against its schema and rulebook rows — owned by its team, never written by another.",
            [f"<estate>/{DATASETS[n]}", f"metamodel/{DATASETS[n]}", f"sdem check · agent sdem-{lvl.lower()}-…"],
            [f"{ents[lvl]} entity types", f"{within[lvl]} links allowed inside", f"{recs[lvl]} records across the projects"], 'Ingestion from the organisation\'s tools (v0.11)', ['entities', 'within'], w=272)
    E = []
    def edge(s_, t, label='', style='solid'): E.append({'s': s_, 't': t, 'label': label, 'style': style})
    edge('bian', 'engine', 'BIAN reference'); edge('bian', 'aid', 'catalogue'); edge('history', 'engine', 'past designs', 'dashed')
    edge('metamodel', 'engine', 'rules'); edge('metamodel', 'validation', 'rules'); edge('engine', 'aid', 'engine rules (F1, R2)')
    edge('engine', 'validation', 'proposed links'); edge('validation', 'kg', 'approved mappings')
    edge('models', 'engine', 'architecture datasets'); edge('kg', 'models', 'federated references / queries', 'both')
    edge('aid', 'projections', 'projected design'); edge('projections', 'kg', 'gap analysis (never merged)', 'dashed')
    edge('coordination', 'models', 'change sets (one layer each)'); edge('coordination', 'engine', 'new links needed', 'dashed')
    return {'boxes': C, 'edges': E, 'width': 1270, 'height': 712, 'band': {'x': 20, 'y': 588, 'w': 1230, 'h': 116, 'title': 'Independently governed architecture models'}}


def collect_home(estates, project_pages, now=None):
    m = metamodel()
    projects = []
    for e, (page, d) in zip(estates, project_pages):
        open_work = [w for w in d['changes']['work'] if w['history'][-1]['status'] in ('open', 'in_progress', 'blocked')]
        cov = {l: (round(100 * c['linked'] / c['eligible']) if c['eligible'] else None) for l, c in d['coverage'].items()}
        projects.append({'name': d['name'], 'path': str(e), 'page': page, 'layers': {l['level']: l['records'] for l in d['layers']},
                         'missing': [x['level'] for x in d['missing_layers']], 'errors': sum(len(l['errors']) for l in d['layers']) + len(d['registry']['errors']) + len(d['coordination']['issues']),
                         'advice': sum(len(l['advice']) for l in d['layers']), 'links': d['registry']['links'], 'by_status': d['registry']['by_status'], 'coverage': cov,
                         'proposals': len(d['review']['rows']), 'open_work': len(open_work), 'events': len(d['changes']['events']),
                         'attention': [a['text'] for a in d['attention'] if a['level'] != 'good']})
    hl = health(m)
    return {'generated': now or datetime.datetime.now().replace(microsecond=0).isoformat(sep=' '), 'metamodel': m, 'entity_picture': layout(m['entities'], m['cross']),
            'architecture': components(m, hl, projects), 'health': hl, 'config': config(), 'projects': projects,
            'package_version': re.search(r'^version = "([^"]+)"', (ROOT / 'pyproject.toml').read_text(), re.M).group(1)}


def write(out, roots=(), estates=(), now=None):
    from . import dashboard
    out = Path(out); (out / 'projects').mkdir(parents=True, exist_ok=True)
    ests = find_estates(roots, estates); pages = []
    for e in ests:
        d = dashboard.collect(e, now=now); d['home'] = '../index.html'
        name = re.sub(r'[^A-Za-z0-9_.-]+', '-', e.resolve().name)
        (out / 'projects' / f'{name}.html').write_text(dashboard.render(d), encoding='utf-8'); pages.append((f'projects/{name}.html', d))
    data = collect_home(ests, pages, now)
    (out / 'index.html').write_text(PAGE.replace('__DATA__', json.dumps(data, ensure_ascii=False).replace('</', '<\\/')), encoding='utf-8')
    return out / 'index.html', data


def main(argv=None):
    ap = argparse.ArgumentParser(prog='sdem home', formatter_class=argparse.RawDescriptionHelpFormatter,
                                 description='Write the main dashboard: SDEM itself — the metamodel (entity types, links inside and between architectures, the engine\'s rules), '
                                             'the metamodel picture, configuration and health — and every project in use, each with its own dashboard. Offline; regenerate after a change.',
                                 epilog='Examples:\n  sdem home -o work/sdem                         # the example estates in examples/\n'
                                        '  sdem home --root projects --estate work/est -o work/sdem')
    ap.add_argument('-o', '--out', default='work/sdem', metavar='DIR', help='output folder (default work/sdem)')
    ap.add_argument('--root', action='append', default=[], metavar='DIR', help='a folder of estates (repeatable; default examples/)')
    ap.add_argument('--estate', action='append', default=[], metavar='DIR', help='one more estate (repeatable)')
    ap.add_argument('--json', action='store_true')
    a = ap.parse_args(argv)
    roots = a.root or ([] if a.estate else [str(ROOT / 'examples')])
    page, data = write(a.out, roots, a.estate)
    if a.json: print(json.dumps(data, indent=2, ensure_ascii=False)); return 0
    h = data['health']; ok = all(g['current'] for g in h['generators']) and all(x['passed'] for x in h['acceptance'])
    print(f"wrote {page} and {len(data['projects'])} project dashboard(s) in {Path(a.out) / 'projects'} — SDEM health: {'OK' if ok else 'ATTENTION'}; "
          f"{sum(1 for p in data['projects'] if p['errors'] or p['proposals'] or p['open_work'])} project(s) need attention")
    print(f"open: file://{page.resolve()}")
    return 0


PAGE = r'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>SDEM — home</title>
<style>
:root{--bg:#f7f6f2;--panel:#fff;--fg:#1d1d1b;--muted:#64625c;--line:#dcd9cf;--accent:#2f6f9f;--good:#2e7d32;--warn:#b26a00;--bad:#c62828;--chip:#efece4;--band:#f0ede5;
--a1:#b5651d;--a2:#2f6f9f;--a3:#4f7f3a;--a4:#7a4f9a}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#151513;--panel:#1e1e1b;--fg:#ecebe6;--muted:#a3a19a;--line:#3a3934;--accent:#7cb3dd;--good:#81c784;--warn:#ffb74d;--bad:#ef9a9a;--chip:#2a2a26;--band:#22211e;--a1:#e0995a;--a2:#7cb3dd;--a3:#8dbd73;--a4:#b98fd8}}
:root[data-theme="dark"]{--bg:#151513;--panel:#1e1e1b;--fg:#ecebe6;--muted:#a3a19a;--line:#3a3934;--accent:#7cb3dd;--good:#81c784;--warn:#ffb74d;--bad:#ef9a9a;--chip:#2a2a26;--band:#22211e;--a1:#e0995a;--a2:#7cb3dd;--a3:#8dbd73;--a4:#b98fd8}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:14px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif}
header{padding:14px 16px 0;border-bottom:1px solid var(--line);background:var(--panel)}.top{display:flex;flex-wrap:wrap;gap:6px 16px;align-items:baseline;justify-content:space-between}
h1{font-size:18px;margin:0}.muted{color:var(--muted);font-size:12px}nav{display:flex;flex-wrap:wrap;gap:2px;margin-top:10px}
nav button{font:inherit;border:0;background:none;color:var(--muted);padding:8px 12px;border-bottom:3px solid transparent;cursor:pointer}
nav button[aria-selected="true"]{color:var(--fg);border-bottom-color:var(--accent);font-weight:600}
button:focus-visible,input:focus-visible,select:focus-visible,a:focus-visible{outline:2px solid var(--accent);outline-offset:1px}
main{padding:16px;max-width:1280px;margin:0 auto}section[hidden]{display:none}h2{font-size:16px;margin:18px 0 8px}h3{font-size:14px;margin:14px 0 6px}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:10px}.card{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:10px 12px}
.big{font-size:22px;font-weight:600}.ok{color:var(--good)}.warn{color:var(--warn)}.bad{color:var(--bad)}
table{border-collapse:collapse;width:100%;background:var(--panel);border:1px solid var(--line);font-size:13px}th,td{text-align:left;padding:6px 8px;border-bottom:1px solid var(--line);vertical-align:top}
th{color:var(--muted);font-weight:600;background:var(--chip);position:sticky;top:0}.chip{display:inline-block;background:var(--chip);border-radius:10px;padding:0 8px;font-size:12px;margin:1px 2px 1px 0}
code{font:12px ui-monospace,SFMono-Regular,Menlo,monospace}.lvl{display:inline-block;width:8px;height:8px;border-radius:2px;margin-right:6px;vertical-align:middle}
.tool{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:8px 0}.tool input,.tool select,.tool button{font:inherit;font-size:13px;border:1px solid var(--line);background:var(--panel);color:var(--fg);border-radius:6px;padding:4px 8px}
.tool input{min-width:260px}.note{font-size:12px;color:var(--muted);margin:4px 0 10px}a{color:var(--accent)}
.split{display:flex;flex-wrap:wrap;gap:12px}.split>.pic{flex:1 1 640px;min-width:0;overflow:auto;background:var(--panel);border:1px solid var(--line);border-radius:8px;max-height:72vh}
.split>.side{flex:0 1 380px;min-width:280px;background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:10px 12px;max-height:72vh;overflow:auto}
svg text{fill:var(--fg);font-size:11px}.band{fill:var(--band)}.bandlbl{font-size:13px;font-weight:600;fill:var(--muted)}.node rect{fill:var(--panel);stroke-width:1.6;cursor:pointer}
.node.abs rect{stroke-dasharray:4 3}.comp rect{fill:var(--panel)}.comp.sel rect{stroke-width:3}.node.sel rect{stroke:var(--fg);stroke-width:3}.e{fill:none;stroke:var(--accent);stroke-width:1.3;opacity:.7}.elbl{font-size:10px;fill:var(--muted)}
.scroll{max-height:60vh;overflow:auto;border:1px solid var(--line)}
main.wide{max-width:none;padding:12px 16px}
.split>.pic.fit{max-height:none;overflow:hidden;display:flex;align-items:flex-start;justify-content:center;padding:6px}
.pic.fit svg{width:100%;height:auto;max-height:calc(100vh - 150px);display:block}
.split>.side.fit{flex:0 0 340px;max-height:calc(100vh - 150px);position:sticky;top:8px}
.pic.fit:fullscreen{background:var(--bg);align-items:center;padding:16px}.pic.fit:fullscreen svg{max-height:100vh;height:100%}
.fsbtn{font:inherit;font-size:12px;border:1px solid var(--line);background:var(--panel);color:var(--fg);border-radius:6px;padding:3px 10px;cursor:pointer;margin-left:6px}
@media (max-width:900px){.split>.side.fit{flex:1 1 100%;position:static;max-height:none}}
@media print{header nav,.tool,#theme{display:none}section{display:block!important}section+section{page-break-before:always}.scroll,.pic,.side{max-height:none;overflow:visible}}
</style></head><body>
<header><div class="top"><div><h1>SDEM — Service Domain Enterprise Metamodel</h1><div class="muted" id="sub"></div></div>
<div class="tool"><button id="theme" aria-label="Toggle light or dark">◐ theme</button><button onclick="window.print()">print</button></div></div><nav role="tablist" id="tabs"></nav></header>
<main id="main"></main>
<script>
const D = __DATA__;
const TABS=[["picture","SDEM architecture"],["home","Overview"],["projects","Projects"],["entities","Architecture entities"],["entitymap","Entity map"],["within","Links inside each architecture"],["cross","Links between architectures"],["rules","Engine rules"],["health","Health"],["config","Configuration"]];
const COL={A1:"var(--a1)",A2:"var(--a2)",A3:"var(--a3)",A4:"var(--a4)"};const M=D.metamodel,H=D.health;
function esc(s){return String(s==null?"":s).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));}
function lvl(l){return `<span class="lvl" style="background:${COL[l]||"var(--muted)"}"></span>${esc(l)}`;}
function lvlOf(t){const m=String(t||"").match(/^(A[1-4])\./);return m?m[1]:"";}
function table(head,rows,cls){return `<div class="${cls||""}"><table><thead><tr>${head.map(h=>`<th>${esc(h)}</th>`).join("")}</tr></thead><tbody>${rows.join("")||`<tr><td colspan="${head.length}" class="muted">none</td></tr>`}</tbody></table></div>`;}
function filterBox(id,ph){return `<div class="tool"><input id="${id}" placeholder="${esc(ph)}" aria-label="Filter"></div>`;}
document.getElementById("sub").textContent=`metamodel ${M.version} · package ${D.package_version} · generated ${D.generated} · offline, read-only`;
const genOK=H.generators.every(g=>g.current),accOK=H.acceptance.every(a=>a.passed);
const R={};
R.home=()=>{
  const n=l=>M.entities.filter(e=>e.level===l&&!e.artefact).length;
  let h=`<h2>SDEM health</h2><div class="cards">
   <div class="card"><b>Generated documents</b><div class="big ${genOK?"ok":"bad"}">${genOK?"current":"stale"}</div><div class="muted">${H.generators.filter(g=>g.current).length} of ${H.generators.length} generators current</div></div>
   <div class="card"><b>Rules engine</b><div class="big ${accOK?"ok":"bad"}">${H.acceptance.filter(a=>a.passed).length} of ${H.acceptance.length}</div><div class="muted">acceptance cases pass (run now)</div></div>
   <div class="card"><b>Controls</b><div class="big">${H.built_controls}</div><div class="muted">of ${H.controls_total} built · ${H.control_gaps.length} known gaps</div></div>
   <div class="card"><b>Spec gaps</b><div class="big">${H.spec_gaps.filter(g=>/^open/.test(g.status)).length}</div><div class="muted">open of ${H.spec_gaps.length} (the rest decided)</div></div></div>`;
  h+=`<h2>The metamodel</h2><div class="cards">${["A1","A2","A3","A4"].map(l=>`<div class="card">${lvl(l)} <b>${esc(l)}</b><div class="big">${n(l)}</div><div class="muted">entity types · ${M.within.filter(w=>w.level===l).length} links allowed inside</div></div>`).join("")}
   <div class="card"><b>Between architectures</b><div class="big">${M.cross.length}</div><div class="muted">link types · ${M.rules.length} engine rules</div></div></div>`;
  const att=D.projects.filter(p=>p.errors||p.proposals||p.open_work);
  h+=`<h2>Projects (${D.projects.length})</h2><p class="note">${att.length?`${att.length} need attention.`:"None needs attention."} Open a project for its own dashboard.</p>`+projTable();
  return h;};
function projTable(){return table(["Project","Architectures (records)","Links","Coverage","Errors","Advice","To review","Open work","Needs attention"],D.projects.map(p=>`<tr>
  <td><a href="${esc(p.page)}"><b>${esc(p.name)}</b></a><div class="muted">${esc(p.path)}</div></td>
  <td>${["A1","A2","A3","A4"].map(l=>p.layers[l]!=null?`<span class="chip">${lvl(l)}${p.layers[l]}</span>`:`<span class="chip muted">${esc(l)} —</span>`).join("")}</td>
  <td>${p.links}<div class="muted">${Object.entries(p.by_status).map(([k,v])=>`${v} ${esc(k)}`).join(", ")}</div></td>
  <td>${Object.entries(p.coverage).map(([l,v])=>`<div>${lvl(l)}${v==null?"—":v+"%"}</div>`).join("")}</td>
  <td class="${p.errors?"bad":"ok"}">${p.errors}</td><td class="${p.advice?"warn":""}">${p.advice}</td><td class="${p.proposals?"warn":""}">${p.proposals}</td><td class="${p.open_work?"warn":""}">${p.open_work}</td>
  <td>${p.attention.map(esc).join("<br>")||'<span class="ok">nothing</span>'}</td></tr>`));}
R.projects=()=>`<h2>Projects in use</h2><p class="note">Every estate found. Coverage = records linked to another architecture by an approved link, of those the rulebook expects to be linked. Regenerate with <code>sdem home</code>.</p>`+projTable();
R.entities=()=>`<h2>Architecture entities</h2><p class="note">The entity types of each architecture, where each comes from, and its evidence status. Dashed = abstract (groups others, never has records of its own).</p>`+filterBox("fEnt","filter: type, standard, definition …")+
  table(["Architecture","Entity type","Definition","Comes from","Evidence status","Attributes","Links inside · between"],M.entities.map(e=>`<tr data-f="${esc((e.type+" "+e.definition+" "+e.standard+" "+e.concept+" "+e.evidence_status).toLowerCase())}">
  <td>${lvl(e.level)}</td><td><b>${esc(e.type)}</b>${e.abstract?' <span class="chip">abstract</span>':""}${e.artefact?' <span class="chip">artefact</span>':""}${e.extends?`<div class="muted">extends ${esc(e.extends)}</div>`:""}</td>
  <td>${esc(e.definition)}</td><td>${esc(e.standard)}${e.concept?`<div class="muted">${esc(e.concept)} ${esc(e.locator)}</div>`:""}</td><td><span class="chip">${esc(e.evidence_status)}</span></td>
  <td>${e.attributes.length}${e.inherited.length?` <span class="muted">+${e.inherited.length} inherited</span>`:""}${e.attributes.filter(a=>a.required).length?`<div class="muted">required: ${e.attributes.filter(a=>a.required).map(a=>esc(a.name)).join(", ")}</div>`:""}</td>
  <td>${e.within.length} · ${e.cross.length}</td></tr>`),"scroll");
R.picture=()=>{const A=D.architecture;const st={"built":0,"partial":0,"not built":0};A.boxes.forEach(b=>st[b.status]=(st[b.status]||0)+1);
  return `<h2>SDEM architecture</h2><p class="note">The components of SDEM and how they work together — the mapping lane (left and centre) and the planning lane, AID (right), over the four independently governed architectures. Click a component for what it is, where it lives, its live figures and what is next. <span class="chip ok">■ built ${st["built"]}</span><span class="chip warn">■ partly built ${st["partial"]}</span><span class="chip muted">▢ not built ${st["not built"]}</span></p>
  <div class="split"><div class="pic fit" id="arch"></div><div class="side fit" id="aside"><p><button class="fsbtn" data-fs="arch" aria-label="Show the diagram full screen">⛶ full screen</button></p><p class="muted">Click a component.</p><h3>Health now</h3><p>${genOK?'<span class="ok">generated documents current</span>':'<span class="bad">generated documents stale</span>'} · ${accOK?'<span class="ok">engine acceptance '+H.acceptance.length+' of '+H.acceptance.length+'</span>':'<span class="bad">engine acceptance failing</span>'}</p><p>${D.projects.length} project(s); ${D.projects.filter(p=>p.errors||p.proposals||p.open_work).length} need attention — see <a href="#projects" data-tab="projects">Projects</a>.</p></div></div>`;};
R.entitymap=()=>`<h2>Entity map</h2><p class="note">The entity types of the four architectures and the ${M.cross.length} link types between them. Click a type for its definition, attributes, the links allowed for it, and the engine rules that use it.</p>
  <div class="split"><div class="pic fit" id="pic"></div><div class="side fit" id="side"><p><button class="fsbtn" data-fs="pic" aria-label="Show the map full screen">⛶ full screen</button></p><p class="muted">Click an entity type.</p></div></div>`;
R.within=()=>`<h2>Links inside each architecture</h2><p class="note">The ${M.within.length} relationship rows allowed within an architecture, each from its reference architecture (BIAN for A2; ArchiMate 3.2 and TOGAF for A1, A3, A4). <code>sdem check</code> rejects any other.</p>`+filterBox("fWithin","filter: type, kind, id …")+
  table(["ID","Architecture","Source","Kind","Target","Basis","Meaning"],M.within.map(w=>`<tr data-f="${esc((w.id+" "+w.source+" "+w.kind+" "+w.target+" "+w.description).toLowerCase())}"><td><code>${esc(w.id)}</code>${w.official?`<div class="muted">${esc(w.official)}</div>`:""}</td><td>${lvl(w.level)}</td><td>${esc(w.source)}</td><td><span class="chip">${esc(w.kind)}</span></td><td>${esc(w.target)}</td><td class="muted">${esc(w.basis)}</td><td>${esc(w.description)}</td></tr>`),"scroll");
R.cross=()=>`<h2>Links between architectures</h2><p class="note">The only ${M.cross.length} link types allowed between architectures — the mapping relationships of the federated knowledge graph — with the evidence each needs before a person approves it.</p>`+
  table(["Link","From","To","Means","Evidence to approve","Source and confidence"],M.cross.map(x=>`<tr><td><b>${esc(x.relationship)}</b><div class="muted">${esc(x.cardinality)}</div></td><td>${lvl(lvlOf(x.source))}${esc(x.source)}</td><td>${lvl(lvlOf(x.target))}${esc(x.target)}</td><td>${esc(x.meaning)}</td><td>${x.evidence.map(e=>`<span class="chip">${esc(e)}</span>`).join("")}</td><td class="muted">${esc(x.source_reference)}<div><b>${esc(x.confidence)}</b> — ${esc(x.verification)}</div></td></tr>`));
R.rules=()=>`<h2>Engine rules</h2><p class="note">The ${M.rules.length} rules of the rules engine (<code>sdem link</code>), each with its step, decision, confidence and published source. Steps: ${Object.entries(M.steps).map(([k,v])=>`<b>${esc(k)}</b> ${esc(v.split(" — ")[0])}`).join(" · ")}.</p>`+filterBox("fRules","filter: id, type, decision, source …")+
  table(["Rule","From","Produces","To","Step","Decision","Confidence","Published source"],M.rules.map(r=>`<tr data-f="${esc((r.id+" "+r.source+" "+r.relation+" "+r.target+" "+r.decision+" "+r.source_reference).toLowerCase())}"><td><b>${esc(r.id)}</b></td><td>${lvl(lvlOf(r.source))}${esc(r.source)}</td><td>${esc(r.relation)}</td><td>${lvl(lvlOf(r.target))}${esc(r.target)}</td><td>${esc(r.step)}</td><td><span class="chip" title="${esc(M.decisions[r.decision]||"")}">${esc(r.decision)}</span></td><td>${esc(r.confidence)}</td><td class="muted">${esc(r.source_reference)}</td></tr>`),"scroll");
R.health=()=>{let h=`<h2>Health</h2><p class="note">Checked when this page was generated.</p><h3>Generated documents and schemas</h3><p class="note">Each must equal a fresh generation from the rulebook (as CI checks).</p>`+
  table(["Generator","Current"],H.generators.map(g=>`<tr><td><code>${esc(g.name)}</code></td><td class="${g.current?"ok":"bad"}">${g.current?"current":"stale — run sdem model regenerate"}</td></tr>`));
  h+=`<h3>Rules engine — acceptance cases (run now)</h3><p class="note">The engine must score at least the hand-executed runs on every case.</p>`+table(["Case","Estate","Engine precision · recall","Floor (hand-run)","Result"],H.acceptance.map(a=>`<tr><td><b>${esc(a.case)}</b></td><td>${esc(a.estate)}</td><td>${a.precision} · ${a.recall}</td><td class="muted">${a.floor_precision} · ${a.floor_recall}</td><td class="${a.passed?"ok":"bad"}">${a.passed?"pass":"FAIL"}</td></tr>`));
  h+=`<h3>Evidence status of the entity types</h3><div>${Object.entries(H.evidence_status).map(([k,v])=>`<span class="chip">${esc(k)}: ${v}</span>`).join("")}</div>`;
  h+=`<h3>Controls</h3>`+table(["Control","Status","Enforces","Last tested (good · bad)"],H.controls.rows.map(c=>`<tr><td><b>${esc(c.id)}</b></td><td>${esc(c.status)}</td><td>${esc(c.control)}</td><td>${esc(c.tested)}</td></tr>`),"scroll");
  h+=`<h3>Known gaps</h3>`+table(["Gap","Not controlled","Risk"],H.control_gaps.map(g=>`<tr><td><b>${esc(g.id)}</b></td><td>${esc(g.not_controlled)}</td><td>${esc(g.risk)}</td></tr>`));
  h+=`<h3>Differences from the high-level spec (gap register)</h3>`+table(["Gap","Kind","What is implemented","Status"],H.spec_gaps.map(g=>`<tr><td><b>${esc(g.id)}</b></td><td>${esc(g.kind)}</td><td>${esc(g.implemented)}</td><td class="${/^open/.test(g.status)?"warn":""}">${esc(g.status)}</td></tr>`),"scroll");
  return h;};
R.config=()=>{const C=D.config;let h=`<h2>Configuration</h2><p class="note">The settings SDEM runs on, and where they live. Change them only through the rulebook files and their checks.</p>`;
  h+=`<h3>Where the configuration lives</h3>`+table(["File","Holds"],C.files.map(f=>`<tr><td><code>${esc(f.file)}</code></td><td>${esc(f.holds)}</td></tr>`));
  h+=`<h3>Confidence bands</h3><div>${Object.entries(C.bands).map(([k,v])=>`<span class="chip">${esc(k)} = ${v}</span>`).join("")}</div><p class="note">${esc(typeof C.confidence_rule==="string"?C.confidence_rule:JSON.stringify(C.confidence_rule||""))}</p>`;
  h+=`<h3>Link statuses and allowed changes</h3>`+table(["From","May become"],Object.entries(C.transitions).map(([k,v])=>`<tr><td><b>${esc(k)}</b></td><td>${v.map(x=>`<span class="chip">${esc(x)}</span>`).join("")||'<span class="muted">final</span>'}</td></tr>`));
  h+=`<h3>Impact rules (version ${esc(C.impact.version)})</h3>`+table(["Change","Reason","Classification by relation"],Object.entries(C.impact.kinds).map(([k,v])=>`<tr><td><b>${esc(k)}</b>${C.impact.supersede_for.includes(k)?'<div class="muted">supersedes links</div>':""}</td><td>${esc(v.reason)}</td><td>${Object.entries(v.rules).map(([r,c])=>`<span class="chip">${esc(r)}: ${esc(c)}</span>`).join("")}</td></tr>`));
  h+=`<h3>Agents (optional — GitHub Copilot)</h3><p>${C.agents["layer agents"].map(a=>`<code>${esc(a)}</code>`).join(" · ")} · orchestrator <code>${esc(C.agents.orchestrator)}</code></p>`;
  return h;};
function drawArchitecture(){const A=D.architecture,host=document.getElementById("arch");if(!host||host.dataset.done)return;host.dataset.done="1";const NS="http://www.w3.org/2000/svg";
  const svg=document.createElementNS(NS,"svg");svg.setAttribute("viewBox",`0 0 ${A.width} ${A.height}`);svg.setAttribute("preserveAspectRatio","xMidYMin meet");svg.setAttribute("role","img");svg.setAttribute("aria-label","SDEM component architecture");host.appendChild(svg);
  const el=(t,a,p)=>{const e=document.createElementNS(NS,t);for(const k in a)e.setAttribute(k,a[k]);(p||svg).appendChild(e);return e;};
  const defs=el("defs",{});const mk=el("marker",{id:"ah",viewBox:"0 0 10 10",refX:"9",refY:"5",markerWidth:"7",markerHeight:"7",orient:"auto-start-reverse"},defs);el("path",{d:"M0,0 L10,5 L0,10 z",fill:"var(--accent)"},mk);
  const BD=A.band;el("rect",{class:"band",x:BD.x,y:BD.y,width:BD.w,height:BD.h,rx:8});const bt=el("text",{class:"bandlbl",x:BD.x+BD.w/2,y:BD.y+18,"text-anchor":"middle"});bt.textContent=BD.title;
  const B={};A.boxes.forEach(b=>B[b.id]=b);B.models={x:BD.x,y:BD.y,w:BD.w,h:BD.h,band:true};const eg=el("g",{}),ng=el("g",{});
  const anchor0=(a,b)=>{const ax=a.x+a.w/2,ay=a.y+a.h/2,bx=b.x+b.w/2,by=b.y+b.h/2;if(Math.abs(by-ay)<a.h){return ax<bx?[[a.x+a.w,ay],[b.x,by]]:[[a.x,ay],[b.x+b.w,by]];}return ay<by?[[ax,a.y+a.h],[bx,b.y]]:[[ax,a.y],[bx,b.y+b.h]];};
  const anchor=(a,b)=>{if(b.band){const x=Math.min(Math.max(a.x+a.w/2,b.x+30),b.x+b.w-30);return[[a.x+a.w/2,a.y+a.h],[x,b.y]];}if(a.band){const x=Math.min(Math.max(b.x+b.w/2,a.x+30),a.x+a.w-30);return[[x,a.y],[b.x+b.w/2,b.y+b.h]];}return anchor0(a,b);};
  A.edges.forEach(e=>{const a=B[e.s],b=B[e.t];if(!a||!b)return;const[[x1,y1],[x2,y2]]=anchor(a,b);const vertical=Math.abs(y2-y1)>=Math.abs(x2-x1)*0.3;
    const d=vertical?`M${x1},${y1} C${x1},${(y1+y2)/2} ${x2},${(y1+y2)/2} ${x2},${y2}`:`M${x1},${y1} C${(x1+x2)/2},${y1} ${(x1+x2)/2},${y2} ${x2},${y2}`;
    const p=el("path",{class:"e",d:d,"marker-end":"url(#ah)"},eg);if(e.style==="both")p.setAttribute("marker-start","url(#ah)");if(e.style==="dashed"||e.style==="both")p.setAttribute("stroke-dasharray","5 4");
    const ti=el("title",{},p);ti.textContent=`${a.title} → ${b.title}${e.label?": "+e.label:""}`;
    if(e.label){const l=el("text",{class:"elbl",x:(x1+x2)/2+4,y:(y1+y2)/2-3},eg);l.textContent=e.label;}});
  const stroke={"built":"var(--accent)","partial":"var(--warn)","not built":"var(--muted)"};
  A.boxes.forEach(b=>{const g=el("g",{class:"node comp",transform:`translate(${b.x},${b.y})`,tabindex:0,role:"button","aria-label":b.title},ng);
    const r=el("rect",{width:b.w,height:b.h,rx:6,stroke:stroke[b.status]||"var(--line)"},g);if(b.status==="not built")r.setAttribute("stroke-dasharray","5 4");
    b.lines.forEach((ln,i)=>{const t=el("text",{x:b.w/2,y:(b.lines.length>1?20:28)+i*15,"text-anchor":"middle",style:"font-weight:600;font-size:12px"},g);t.textContent=ln;});
    const t2=el("text",{x:b.w/2,y:b.h-12,"text-anchor":"middle",style:"fill:var(--muted);font-size:10px"},g);t2.textContent=b.sub.length>44?b.sub.slice(0,43)+"…":b.sub;
    if(b.status!=="built"){const t3=el("text",{x:b.w-6,y:12,"text-anchor":"end",style:`fill:${stroke[b.status]};font-size:9px;font-weight:700`},g);t3.textContent=b.status.toUpperCase();}
    const ti=el("title",{},g);ti.textContent=`${b.title} — ${b.status}`;
    const pick=()=>{ng.querySelectorAll(".comp").forEach(x=>x.classList.remove("sel"));g.classList.add("sel");showComponent(b.id);};g.addEventListener("click",pick);g.addEventListener("keydown",ev=>{if(ev.key==="Enter")pick();});});}
function showComponent(id){const b=D.architecture.boxes.find(x=>x.id===id);const side=document.getElementById("aside");if(!b||!side)return;
  const names=Object.fromEntries(TABS);const cls={"built":"ok","partial":"warn","not built":"muted"}[b.status];
  side.innerHTML=`<h3>${esc(b.title)}</h3><p><span class="chip ${cls}">${esc(b.status)}</span> <span class="muted">${esc(b.sub)}</span></p><p>${esc(b.what)}</p>
   <h3>Figures now</h3>${b.figures.map(f=>`<div>• ${esc(f)}</div>`).join("")}
   <h3>Where it lives</h3>${b.where.map(w=>`<div><code>${esc(w)}</code></div>`).join("")}
   <h3>Next</h3><p>${esc(b.next)}</p>${b.tabs.length?`<h3>More</h3><p>${b.tabs.map(t=>`<a href="#${t}" data-tab="${t}">${esc(names[t]||t)}</a>`).join(" · ")}</p>`:""}`;}
function drawPicture(){const P=D.entity_picture,host=document.getElementById("pic");if(!host||host.dataset.done)return;host.dataset.done="1";const NS="http://www.w3.org/2000/svg";const[W,Hh]=P.box;
  const svg=document.createElementNS(NS,"svg");svg.setAttribute("viewBox",`0 0 ${P.width} ${P.height}`);svg.setAttribute("preserveAspectRatio","xMidYMin meet");svg.setAttribute("role","img");svg.setAttribute("aria-label","Metamodel picture");host.appendChild(svg);
  const el=(t,a,p)=>{const e=document.createElementNS(NS,t);for(const k in a)e.setAttribute(k,a[k]);(p||svg).appendChild(e);return e;};
  P.bands.forEach(b=>{el("rect",{class:"band",x:8,y:b.y,width:P.width-16,height:b.h,rx:8});const t=el("text",{class:"bandlbl",x:18,y:b.y+20});t.textContent=b.title;});
  const pos={};P.nodes.forEach(n=>pos[n.type]=n);const eg=el("g",{}),ng=el("g",{});
  P.edges.forEach(e=>{const s=pos[e.s],t=pos[e.t];const x1=s.x+W/2,y1=s.y+Hh,x2=t.x+W/2,y2=t.y;const my=(y1+y2)/2;const p=el("path",{class:"e",d:`M${x1},${y1} C${x1},${my} ${x2},${my} ${x2},${y2}`},eg);
    const ti=el("title",{},p);ti.textContent=`${e.s} ${e.rel} ${e.t}`;const l=el("text",{class:"elbl",x:(x1+x2)/2+4,y:my},eg);l.textContent=e.rel;});
  P.nodes.forEach(n=>{const g=el("g",{class:"node"+(n.abstract?" abs":""),transform:`translate(${n.x},${n.y})`,tabindex:0},ng);el("rect",{width:W,height:Hh,rx:6,stroke:COL[n.level]},g);
    const t=el("text",{x:8,y:22},g);t.textContent=n.type.split(".")[1];const ti=el("title",{},g);ti.textContent=n.type;
    const pick=()=>{ng.querySelectorAll(".node").forEach(x=>x.classList.remove("sel"));g.classList.add("sel");showType(n.type);};g.addEventListener("click",pick);g.addEventListener("keydown",ev=>{if(ev.key==="Enter")pick();});});}
function showType(t){const e=M.entities.find(x=>x.type===t);const side=document.getElementById("side");if(!e||!side)return;
  const rows=(a)=>a.map(x=>`<tr><td><code>${esc(x.name)}</code>${x.required?' <span class="chip">required</span>':""}</td><td class="muted">${esc(x.type)}</td><td>${esc(x.description)}</td></tr>`).join("");
  side.innerHTML=`<h3>${lvl(e.level)} ${esc(e.type)}</h3><p>${esc(e.definition)}</p><p class="muted">${esc(e.standard)} ${esc(e.concept)} ${esc(e.locator)} · <span class="chip">${esc(e.evidence_status)}</span>${e.extends?` · extends ${esc(e.extends)}`:""}</p>
   <h3>Attributes</h3>${e.attributes.length||e.inherited.length?`<table><tbody>${rows(e.attributes)}${rows(e.inherited)}</tbody></table>`:'<p class="muted">core fields only</p>'}
   <h3>Links between architectures</h3>${e.cross.map(x=>`<div>${esc(x)}</div>`).join("")||'<p class="muted">none</p>'}
   <h3>Links inside its architecture</h3><div>${e.within.map(x=>`<span class="chip">${esc(x)}</span>`).join("")||'<span class="muted">none</span>'}</div>
   <h3>Engine rules that use it</h3><div>${e.rules.map(x=>`<span class="chip">${esc(x)}</span>`).join("")||'<span class="muted">none</span>'}</div>`;}
const nav=document.getElementById("tabs"),main=document.getElementById("main");
TABS.forEach(([id,label])=>{const b=document.createElement("button");b.textContent=label;b.setAttribute("role","tab");b.dataset.tab=id;b.id="tab-"+id;nav.appendChild(b);
  const s=document.createElement("section");s.id=id;s.setAttribute("role","tabpanel");s.setAttribute("aria-labelledby","tab-"+id);s.hidden=true;s.innerHTML=R[id]();main.appendChild(s);});
function show(id){if(!document.getElementById(id))id="picture";TABS.forEach(([t])=>{document.getElementById(t).hidden=(t!==id);document.getElementById("tab-"+t).setAttribute("aria-selected",String(t===id));});
  main.classList.toggle("wide",id==="picture"||id==="entitymap");if(id==="picture")drawArchitecture();if(id==="entitymap")drawPicture();try{history.replaceState(null,"","#"+id);}catch(e){}}
nav.addEventListener("click",e=>{const t=e.target.closest("button");if(t)show(t.dataset.tab);});
nav.addEventListener("keydown",e=>{if(e.key!=="ArrowRight"&&e.key!=="ArrowLeft")return;const i=TABS.findIndex(([t])=>!document.getElementById(t).hidden);const n=(i+(e.key==="ArrowRight"?1:TABS.length-1))%TABS.length;show(TABS[n][0]);document.getElementById("tab-"+TABS[n][0]).focus();});
document.addEventListener("click",e=>{const a=e.target.closest&&e.target.closest("a[data-tab]");if(a){e.preventDefault();show(a.dataset.tab);}
  const f=e.target.closest&&e.target.closest("[data-fs]");if(f){const t=document.getElementById(f.dataset.fs);if(document.fullscreenElement)document.exitFullscreen();else if(t&&t.requestFullscreen)t.requestFullscreen();}});
[["fEnt","entities"],["fWithin","within"],["fRules","rules"]].forEach(([f,sec])=>{const i=document.getElementById(f);if(i)i.addEventListener("input",()=>{const q=i.value.toLowerCase();document.querySelectorAll(`#${sec} tr[data-f]`).forEach(r=>{r.hidden=q&&!r.dataset.f.includes(q);});});});
document.getElementById("theme").onclick=()=>{const r=document.documentElement;const dark=r.dataset.theme?r.dataset.theme==="dark":matchMedia("(prefers-color-scheme: dark)").matches;r.dataset.theme=dark?"light":"dark";};
show((location.hash||"#picture").slice(1));
</script></body></html>
'''


if __name__ == '__main__':
    raise SystemExit(main())
