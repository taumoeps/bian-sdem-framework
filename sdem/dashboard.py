"""`sdem dashboard` — one self-contained, read-only HTML page per estate (docs/design/sdem-dashboard-design.md, spec DB-*).

Everything is computed here, with the same functions the CLI uses (checks, the rules engine, trace, impact, matrices,
AID gaps, controls); the page only displays the results and shows the exact `sdem` command for every action. No server,
no network, no AI. Regenerate after a change.
"""
import argparse, collections, datetime, html, json, re, sys
from pathlib import Path

from .store import GraphReader, stale_inputs

from .paths import DATA_ROOT as ROOT, repo_path
FILES = ('a1-business.json', 'a2-service-domain.json', 'a3-application.json', 'a4-technology.json')
LEVEL_NAMES = {'A1': 'A1 Business', 'A2': 'A2 Service domain (BIAN)', 'A3': 'A3 Application', 'A4': 'A4 Technology'}
KINDS = ('modify', 'rehost', 'replace', 'retire')


def _j(p): return json.loads(Path(p).read_text(encoding='utf-8'))


def _compact(tree, fg):
    """A trace tree, compact for display: id, name, type, level, and per child the link id and relationship."""
    inst = fg.instance(tree['id']) or {}
    out = {'id': tree['id'], 'name': inst.get('name') or tree.get('name') or tree['id'], 'type': tree.get('type') or inst.get('type'),
           'level': fg.mm.level(tree.get('type') or inst.get('type') or '') or '?', 'children': []}
    for c in tree.get('children', []):
        out['children'].append({'rel': c['via']['relationship'], 'link': c['via']['mapping_id'], 'node': _compact(c['node'], fg)})
    return out


def _coverage(reader):
    types = _j(ROOT / 'schema' / 'relationship-types.json')['relationships']; out = {}
    for lvl in LEVEL_NAMES:
        nodes = reader.nodes(level=lvl)
        eligible = [n for n in nodes if any(reader.mm.is_a(n['type'], x['source_type']) or reader.mm.is_a(n['type'], x['target_type']) for x in types)]
        unmapped = reader.unmapped(lvl)
        if not nodes: continue
        out[lvl] = {'eligible': len(eligible), 'linked': len(eligible) - len(unmapped), 'unmapped': [{'id': n['id'], 'name': n.get('name'), 'type': n['type'], 'expected': n['expected']} for n in unmapped]}
    return out


def _evidence_needed(rel, source_type, mm):
    for t in _j(ROOT / 'schema' / 'relationship-types.json')['relationships']:
        if t['relationship'] == rel and mm.is_a(source_type, t['source_type']): return t['required_evidence']
    return []


def _controls():
    d = _j(ROOT / 'metamodel' / 'controls.json'); last = {}; tested = []
    for ex in ('use-case-example-1', 'use-case-example-2', 'use-case-example-3'):
        p = repo_path('docs', 'evidence', ex, 'results.json') or Path('/nonexistent')
        if p.exists():
            r = _j(p); tested.append({'example': ex, 'date': r.get('run_date') or r.get('date')})
            last.update({c['id']: f"{c['good']} · {c['bad']}" for c in r.get('controls', [])})
    rows = [{'id': c['id'], 'status': c.get('status', 'built'), 'area': c['rule_area'], 'control': c['control'], 'runs': c['runs'],
             'tested': last.get(c['id']) or ('every push — test suite' if c.get('tested_by') == 'tests' else '—')} for c in d['controls']]
    return {'rows': rows, 'gaps': d['gaps'], 'tested_in': tested}


def collect(estate, proposals=None, projection=None, catalogue=None, graph=None, now=None):
    from .agents import Estate, check_coordination, CoordinationError
    from .cli import _rule_of
    from .matrix import matrices
    estate = Path(estate); files = [str(estate / f) for f in FILES if (estate / f).exists()] + [str(estate / 'mappings.json')]
    present = {lvl for lvl, f in zip(LEVEL_NAMES, FILES) if (estate / f).exists()}
    reader = GraphReader.from_exports(files); fg = reader.fg; mm = reader.mm
    report = fg.check(); warns = fg.warnings
    names = {n['id']: n.get('name') or n['id'] for n in reader.nodes()}
    reg = _j(estate / 'mappings.json'); status = {}
    for m in reg['mappings']: status[m.get('status')] = status.get(m.get('status'), 0) + 1
    layers = []
    for lvl, g in sorted(fg.levels.items()):
        key = next((k for k in list(report) + list(warns) if k.startswith(f'level {lvl} ')), f'level {lvl}')
        layers.append({'level': lvl, 'title': LEVEL_NAMES[lvl], 'model_id': g.doc.get('model_id'), 'records': len(g.instances), 'relationships': len(g.relationships),
                       'errors': report.get(key, []), 'advice': warns.get(key, [])})
    reg_errors = [i for k, v in report.items() if not k.startswith('level ') for i in v]
    coord_issues, coord_n = check_coordination(estate)
    # review: what the rules engine proposes now (approved links excluded), or a given proposals file
    if proposals: props = _j(proposals).get('mappings', []); props_src = str(proposals)
    else:
        from .rules_engine import RulesEngine
        props = RulesEngine().infer(reader, {'id': 'DASH'})['proposals']; props_src = 'the rules engine, run on this estate when the page was generated'
    review = []
    for m in sorted(props, key=lambda m: (m.get('confidence', 0), m['relationship'], m['source']['id'])):
        if m.get('status', 'proposed') != 'proposed': continue
        review.append({'id': m['mapping_id'], 'source': m['source']['id'], 'source_name': names.get(m['source']['id'], ''), 'rel': m['relationship'],
                       'target': m['target']['id'], 'target_name': names.get(m['target']['id'], ''), 'rule': _rule_of(m), 'confidence': m.get('confidence'),
                       'reasoning': re.sub(r'\s*\((?:P|C)-[A-Z0-9]+-\d+\)', '', m.get('rationale', '')), 'evidence_needed': _evidence_needed(m['relationship'], m['source']['type'], mm)})
    # trace and impact for every record (precomputed: the page does not compute)
    records = {}
    for n in sorted(reader.nodes(), key=lambda n: (n['level'], n['id'])):
        rid = n['id']; rec = {'id': rid, 'name': n.get('name') or rid, 'type': n['type'], 'level': n['level']}
        rec['down'] = _compact(fg.trace(rid, 'down'), fg); rec['up'] = _compact(fg.trace(rid, 'up'), fg)
        rec['impact'] = {}
        for k in KINDS:
            r = fg.impact(rid, k)
            rec['impact'][k] = {'reason': r['reason'], 'supersede': r['mappings_to_supersede'],
                                'rows': [{'id': x['id'], 'name': x['name'], 'level': x['level'], 'classification': x['classification'], 'via': x['via'], 'relation': x['relation']} for x in r['instances']]}
        records[rid] = rec
    # changes and work
    events, work, sets = [], [], []
    try:
        if (estate / 'coordination').exists():
            e = Estate(estate); events = e.events(); work = e.work(); sets = [_j(f) for f in e.change_sets()]
    except CoordinationError: pass
    direct = [i for i in coord_issues if 'AG-S08' in i]
    # AID
    aid = None
    if projection:
        from . import aid as _aid
        pkg = _aid.read(projection)
        real = {lvl: _j(estate / f) for lvl, f in zip(('A1', 'A2', 'A3', 'A4'), FILES) if (estate / f).exists()}
        g = _aid.gaps(pkg, real, reg)
        issues = _aid.check(pkg, _j(catalogue) if catalogue else None)
        aid = {'id': pkg['projection']['projection_id'], 'mode': pkg['projection']['mode'], 'have': pkg['projection']['have'], 'summary': pkg['projection']['summary'],
               'ends': pkg['projection']['projection_ends'], 'valid': not issues, 'issues': issues[:20], 'metrics': g['metrics'],
               'elements': [{'level': lvl, 'id': i['id'], 'name': i.get('name'), 'type': i['type'], **{k: i['projection'][k] for k in ('step', 'rule', 'source_reference', 'reasoning', 'confidence')},
                             'inferred_from': i['projection']['inferred_from']} for lvl, d in sorted(pkg['layers'].items()) for i in d['instances'] if not i['type'].endswith(('Attribute', 'Pattern'))],
               'gap_rows': g['rows']}
    stale = None
    if graph:
        b, s = stale_inputs(graph); stale = {'graph': str(graph), 'build': b, 'changed': s}
    # design records and gap records — what did not fit an entity (DB-C09)
    designs = None
    if (estate / 'designs' / 'design-records.json').exists():
        dr = _j(estate / 'designs' / 'design-records.json'); titles = {d['id']: d['title'] for d in dr['documents']}
        open_gaps = [{**{k: g.get(k) for k in ('id', 'category', 'where', 'text', 'about', 'reason')}, 'page': titles.get(g['document'], g['document'])}
                     for g in dr['gaps'] if g['status'] == 'open']
        designs = {'documents': [{k: d.get(k) for k in ('id', 'title', 'modified', 'url', 'facts', 'coverage', 'entities', 'kind')} for d in dr['documents']],
                   'open': open_gaps, 'by_category': dict(collections.Counter(g['category'] for g in open_gaps).most_common()),
                   'by_status': dict(collections.Counter(g['status'] for g in dr['gaps']))}
    attention = []
    errs = sum(len(l['errors']) for l in layers) + len(reg_errors) + len([i for i in coord_issues if 'AG-S08' not in i])
    if errs: attention.append({'text': f'{errs} error(s) in the data — fix before trusting anything else', 'tab': 'overview', 'cmd': f'sdem check --estate {estate}', 'level': 'bad'})
    if direct: attention.append({'text': f'{len(direct)} dataset(s) edited outside a change set (AG-S08)', 'tab': 'changes', 'cmd': f'sdem change adopt --estate {estate} --layer <A?> --person <you> --reason <why>', 'level': 'bad'})
    if review: attention.append({'text': f'{len(review)} proposed link(s) to review', 'tab': 'review', 'cmd': f'sdem review <proposals.json> --estate {estate}', 'level': 'warn'})
    open_work = [w for w in work if w['history'][-1]['status'] in ('open', 'in_progress', 'blocked')]
    if open_work: attention.append({'text': f'{len(open_work)} open work item(s)', 'tab': 'changes', 'cmd': f'sdem work list --estate {estate}', 'level': 'warn'})
    unplanned = [e for e in Estate(estate).status() if not e['planned']] if events else []
    if unplanned: attention.append({'text': f'{len(unplanned)} change event(s) waiting to be planned', 'tab': 'changes', 'cmd': f'sdem work plan --event {unplanned[0]["id"]} --estate {estate} --agent sdem-orchestrator --person <you>', 'level': 'warn'})
    if designs and designs['open']: attention.append({'text': f"{len(designs['open'])} open gap(s) — what did not fit an entity in onboarded designs", 'tab': 'designs', 'cmd': f'sdem designs --estate {estate} --gaps --status open', 'level': 'warn'})
    if stale and stale['changed']: attention.append({'text': f"the graph store {stale['graph']} is out of date", 'tab': 'overview', 'cmd': f"sdem build --estate {estate} --out {stale['graph']}", 'level': 'warn'})
    if not attention: attention.append({'text': 'nothing needs your attention', 'tab': 'overview', 'cmd': '', 'level': 'good'})
    return {'estate': str(estate), 'name': estate.resolve().name, 'generated': now or datetime.datetime.now().replace(microsecond=0).isoformat(sep=' '),
            'metamodel': mm.version, 'layers': layers, 'missing_layers': [{'level': l, 'title': t} for l, t in LEVEL_NAMES.items() if l not in present], 'registry': {'links': len(reg['mappings']), 'by_status': status, 'errors': reg_errors},
            'coordination': {'records': coord_n, 'issues': coord_issues}, 'coverage': _coverage(reader), 'attention': attention,
            'review': {'source': props_src, 'rows': review}, 'records': records, 'kinds': list(KINDS), 'matrix': matrices(fg),
            'changes': {'events': events, 'work': work, 'change_sets': [{k: c.get(k) for k in ('id', 'layer', 'reason', 'agent', 'person', 'created_at', 'event', 'reverts', 'adopted')} | {'changes': len(c.get('changes', []))} for c in sets], 'direct_edits': direct},
            'aid': aid, 'controls': _controls(), 'stale': stale, 'designs': designs}


def render(data, title=None):
    title = title or f"SDEM — {data['name']}"
    blob = json.dumps(data, ensure_ascii=False).replace('</', '<\\/')
    return PAGE.replace('__TITLE__', html.escape(title)).replace('__DATA__', blob)


def main(argv=None):
    ap = argparse.ArgumentParser(prog='sdem dashboard', formatter_class=argparse.RawDescriptionHelpFormatter,
                                 description='Write one self-contained, read-only HTML dashboard for an estate: health, what needs attention, review, trace and impact, '
                                             'matrices, changes and work, AID plans, controls. Opens offline; regenerate after a change.',
                                 epilog='Examples:\n  sdem dashboard --estate examples/payment-initiation -o work/dashboard.html\n'
                                        '  sdem dashboard --estate work/est --graph work/graph --projection work/prj --catalogue bian.json -o work/dashboard.html')
    ap.add_argument('--estate', required=True, metavar='DIR'); ap.add_argument('-o', '--out', metavar='FILE', help='default <estate>/dashboard.html')
    ap.add_argument('--proposals', metavar='FILE', help='show these proposals (default: run the rules engine now)')
    ap.add_argument('--projection', metavar='DIR', help='an AID projection package to show beside the real design')
    ap.add_argument('--catalogue', metavar='FILE', help='the BIAN catalogue the projection used (for its check)')
    ap.add_argument('--graph', metavar='DIR', help='a graph store of this estate — warn when it is out of date')
    ap.add_argument('--title'); ap.add_argument('--json', action='store_true', help='print the computed data instead of writing the page')
    a = ap.parse_args(argv)
    from .cli import _estate_files
    try: _estate_files(a.estate)
    except SystemExit as e: print(f'ERROR: {e}', file=sys.stderr); return 2
    data = collect(a.estate, a.proposals, a.projection, a.catalogue, a.graph)
    if a.json: print(json.dumps(data, indent=2, ensure_ascii=False)); return 0
    out = Path(a.out or Path(a.estate) / 'dashboard.html'); out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render(data, a.title), encoding='utf-8')
    att = '; '.join(x['text'] for x in data['attention'])
    print(f'wrote {out} — {att}. Open it in a browser (or VS Code: Simple Browser).')
    return 0


PAGE = r'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<style>
:root{--bg:#f7f6f2;--panel:#fff;--fg:#1d1d1b;--muted:#64625c;--line:#dcd9cf;--accent:#2f6f9f;--good:#2e7d32;--warn:#b26a00;--bad:#c62828;--chip:#efece4;
--a1:#b5651d;--a2:#2f6f9f;--a3:#4f7f3a;--a4:#7a4f9a}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#151513;--panel:#1e1e1b;--fg:#ecebe6;--muted:#a3a19a;--line:#3a3934;--accent:#7cb3dd;--good:#81c784;--warn:#ffb74d;--bad:#ef9a9a;--chip:#2a2a26;--a1:#e0995a;--a2:#7cb3dd;--a3:#8dbd73;--a4:#b98fd8}}
:root[data-theme="dark"]{--bg:#151513;--panel:#1e1e1b;--fg:#ecebe6;--muted:#a3a19a;--line:#3a3934;--accent:#7cb3dd;--good:#81c784;--warn:#ffb74d;--bad:#ef9a9a;--chip:#2a2a26;--a1:#e0995a;--a2:#7cb3dd;--a3:#8dbd73;--a4:#b98fd8}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:14px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif}
header{padding:14px 16px 0;border-bottom:1px solid var(--line);background:var(--panel)}
.top{display:flex;flex-wrap:wrap;gap:6px 16px;align-items:baseline;justify-content:space-between}
h1{font-size:18px;margin:0}.muted{color:var(--muted);font-size:12px}
nav{display:flex;flex-wrap:wrap;gap:2px;margin-top:10px}
nav button{font:inherit;border:0;background:none;color:var(--muted);padding:8px 12px;border-bottom:3px solid transparent;cursor:pointer}
nav button[aria-selected="true"]{color:var(--fg);border-bottom-color:var(--accent);font-weight:600}
nav button:focus-visible,button:focus-visible,input:focus-visible,select:focus-visible{outline:2px solid var(--accent);outline-offset:1px}
main{padding:16px;max-width:1200px;margin:0 auto}section[hidden]{display:none}
h2{font-size:16px;margin:18px 0 8px}h3{font-size:14px;margin:14px 0 6px}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:10px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:10px 12px}
.card .big{font-size:22px;font-weight:600}.lvl{display:inline-block;width:8px;height:8px;border-radius:2px;margin-right:6px;vertical-align:middle}
.ok{color:var(--good)}.warn{color:var(--warn)}.bad{color:var(--bad)}
table{border-collapse:collapse;width:100%;background:var(--panel);border:1px solid var(--line);border-radius:6px;font-size:13px}
th,td{text-align:left;padding:6px 8px;border-bottom:1px solid var(--line);vertical-align:top}th{color:var(--muted);font-weight:600;background:var(--chip)}
.chip{display:inline-block;background:var(--chip);border-radius:10px;padding:0 8px;font-size:12px;margin:1px 2px 1px 0}
code,.cmd{font:12px ui-monospace,SFMono-Regular,Menlo,monospace}
.cmd{display:flex;gap:6px;align-items:flex-start;background:var(--chip);border-radius:6px;padding:6px 8px;margin:4px 0;word-break:break-all}
.cmd span{flex:1}.cmd button,.tool button,.tool select,.tool input{font:inherit;font-size:12px;border:1px solid var(--line);background:var(--panel);color:var(--fg);border-radius:6px;padding:3px 8px;cursor:pointer}
.tool{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:8px 0}.tool input{min-width:280px;cursor:text}
.att{border-left:4px solid var(--line);padding:6px 10px;margin:6px 0;background:var(--panel)}
.att.bad{border-left-color:var(--bad);color:inherit}.att.warn{border-left-color:var(--warn);color:inherit}.att.good{border-left-color:var(--good);color:inherit}
ul.tree{list-style:none;padding-left:18px;margin:2px 0}ul.tree.root{padding-left:0}.tree li{margin:2px 0}
.rel{color:var(--muted);font-size:12px}.bar{height:8px;background:var(--chip);border-radius:4px;overflow:hidden}.bar i{display:block;height:100%;background:var(--accent)}
details summary{cursor:pointer;color:var(--accent)}.c-design_change_required{color:var(--bad);font-weight:600}.c-review_required{color:var(--warn)}.c-no_impact{color:var(--muted)}
.note{font-size:12px;color:var(--muted);margin:4px 0 10px}
@media print{header nav,.tool,.cmd button,#theme{display:none}section{display:block!important}section+section{page-break-before:always}body{background:#fff}}
</style></head><body>
<header><div class="top"><div><h1>__TITLE__</h1><div class="muted" id="sub"></div></div>
<div class="tool"><button id="theme" aria-label="Toggle light or dark">◐ theme</button><button onclick="window.print()">print</button></div></div>
<nav role="tablist" id="tabs"></nav></header>
<main id="main"></main>
<script>
const D = __DATA__;
const TABS = [["overview","Overview"],["review","Review"],["trace","Trace & impact"],["matrix","Matrices"],["changes","Changes & work"],["designs","Designs & gaps"],["aid","AID plans"],["controls","Controls"]];
const COL = {A1:"var(--a1)",A2:"var(--a2)",A3:"var(--a3)",A4:"var(--a4)"};
const CLS = {design_change_required:"design change required",review_required:"review required",no_impact:"no impact"};
function esc(s){return String(s==null?"":s).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));}
function cmd(c){if(!c)return "";return `<div class="cmd"><span>${esc(c)}</span><button data-copy="${esc(c)}" aria-label="Copy command">copy</button></div>`;}
function lvl(l){return `<span class="lvl" style="background:${COL[l]||"var(--muted)"}"></span>${esc(l)}`;}
function rec(id,name){return `${esc(name||id)} <code>${esc(id)}</code>`;}
function table(head,rows){return `<table><thead><tr>${head.map(h=>`<th>${esc(h)}</th>`).join("")}</tr></thead><tbody>${rows.join("")||`<tr><td colspan="${head.length}" class="muted">none</td></tr>`}</tbody></table>`;}
document.getElementById("sub").textContent = `estate ${D.estate} · generated ${D.generated} · rules ${D.metamodel} · read-only — act with the sdem commands shown`;
if (D.home) { const a = document.createElement("a"); a.href = D.home; a.textContent = "← SDEM home"; a.style.marginRight = "12px"; document.getElementById("sub").prepend(a); }

const R = {};
R.overview = () => {
  let h = `<h2>What needs your attention</h2>` + D.attention.map(a=>`<div class="att ${a.level}">${esc(a.text)}${a.tab!=="overview"?` — <a href="#${a.tab}" data-tab="${a.tab}">open</a>`:""}${cmd(a.cmd)}</div>`).join("");
  h += `<h2>Health of each architecture</h2><div class="cards">` + D.layers.map(l=>{
    const st = l.errors.length?`<span class="bad">${l.errors.length} error(s)</span>`:l.advice.length?`<span class="warn">OK · ${l.advice.length} advice</span>`:`<span class="ok">OK</span>`;
    const c = D.coverage[l.level]||{eligible:0,linked:0,unmapped:[]}; const pct = c.eligible?Math.round(100*c.linked/c.eligible):100;
    return `<div class="card"><div>${lvl(l.level)} <b>${esc(l.title)}</b></div><div class="big">${l.records}</div><div class="muted">records · ${l.relationships} links inside</div><div>${st}</div>
      <div class="muted" style="margin-top:6px">linked to other layers: ${c.linked} of ${c.eligible} (${pct}%)</div><div class="bar"><i style="width:${pct}%"></i></div></div>`;}).join("");
  h += D.missing_layers.map(m=>`<div class="card"><div>${lvl(m.level)} <b>${esc(m.title)}</b></div><div class="big muted">—</div><div class="muted">not in this estate — no dataset. AID can project it.</div></div>`).join("");
  const rs = D.registry; h += `<div class="card"><div><b>Registry</b> (links between layers)</div><div class="big">${rs.links}</div><div class="muted">${Object.entries(rs.by_status).map(([k,v])=>`${v} ${k}`).join(" · ")}</div><div>${rs.errors.length?`<span class="bad">${rs.errors.length} error(s)</span>`:`<span class="ok">OK</span>`}</div></div>`;
  h += `<div class="card"><div><b>Coordination records</b></div><div class="big">${D.coordination.records}</div><div class="muted">change sets, events, work items</div><div>${D.coordination.issues.length?`<span class="bad">${D.coordination.issues.length} issue(s)</span>`:`<span class="ok">OK</span>`}</div></div></div>`;
  const errs = D.layers.flatMap(l=>l.errors.map(e=>[l.level,e])).concat(D.registry.errors.map(e=>["registry",e])).concat(D.coordination.issues.map(e=>["coordination",e]));
  h += `<h2>Errors</h2><p class="note">Each breaks a rule of the metamodel; fix the data and run the check again.</p>` + table(["Where","Message"], errs.map(([w,e])=>`<tr><td>${esc(w)}</td><td>${esc(e)}</td></tr>`)) + cmd(`sdem check --estate ${D.estate}`);
  const adv = D.layers.flatMap(l=>l.advice.map(e=>[l.level,e]));
  h += `<details><summary>Advice (${adv.length}) — things the metamodel recommends but does not require</summary>` + table(["Layer","Advice"], adv.map(([w,e])=>`<tr><td>${esc(w)}</td><td>${esc(e)}</td></tr>`)) + `</details>`;
  const un = Object.entries(D.coverage).flatMap(([l,c])=>c.unmapped.map(u=>[l,u]));
  h += `<h2>Records not yet linked to another layer</h2><p class="note">They have no approved link of a type the metamodel expects for them. The Review tab shows what the rules engine proposes.</p>` +
       table(["Layer","Record","Type","Expected links"], un.map(([l,u])=>`<tr><td>${lvl(l)}</td><td>${rec(u.id,u.name)}</td><td>${esc(u.type)}</td><td>${u.expected.map(x=>`<span class="chip">${esc(x)}</span>`).join("")}</td></tr>`));
  if (D.stale) h += `<p class="note">Graph store ${esc(D.stale.graph)}: ${D.stale.changed.length?`<span class="warn">out of date since build ${D.stale.build}</span>`:"current"}.</p>`;
  return h;
};
R.review = () => {
  const rows = D.review.rows;
  let h = `<h2>Proposed links — weakest first</h2><p class="note">From ${esc(D.review.source)}. A person approves each link they accept, with the evidence its type needs — never the engine or an agent (CTL-21). The approval is final when the change is merged in a reviewed pull request.</p>`;
  h += table(["Confidence","Proposed link","Rule","Why","Evidence needed to approve","Approve (you)"], rows.map(r=>`<tr><td><b>${r.confidence}</b>${r.confidence<=0.4?`<div class="warn" style="font-size:12px">names only — a hint</div>`:""}</td>
    <td>${rec(r.source,r.source_name)}<div class="rel">— ${esc(r.rel)} →</div>${rec(r.target,r.target_name)}</td><td>${esc(r.rule)}</td><td>${esc(r.reasoning)}</td>
    <td>${r.evidence_needed.map(e=>`<span class="chip">${esc(e)}</span>`).join("")}</td>
    <td>${cmd(`sdem approve ${r.id} --proposals <proposals.json> --estate ${D.estate} --reviewer <your name> --evidence ${r.evidence_needed[0]||"<kind>"}:<document>`)}</td></tr>`));
  h += `<p class="note">To get the proposals file for the commands: </p>` + cmd(`sdem link --estate ${D.estate} --out work/links`);
  return h;
};
let current = null;
function treeHtml(n, root){const kids = n.children.map(c=>`<li><span class="rel">— ${esc(c.rel)} (${esc(c.link)}) →</span> ${lvl(c.node.level)} ${rec(c.node.id,c.node.name)}${treeHtml(c.node,false)}</li>`).join("");
  return kids?`<ul class="tree${root?" root":""}">${kids}</ul>`:(root?`<p class="muted">no approved links in this direction</p>`:"");}
R.trace = () => {
  const ids = Object.keys(D.records);
  let h = `<h2>Trace and impact</h2><p class="note">Choose a record (type an id or a name). Traces follow approved links only.</p>
   <div class="tool"><input id="pick" list="recs" placeholder="e.g. CAP-PAY-010 or Payments Hub" aria-label="Record"><datalist id="recs">${ids.map(i=>`<option value="${esc(i)}">${esc(D.records[i].name)} (${esc(D.records[i].level)})</option>`).join("")}</datalist>
   <select id="kind" aria-label="Change kind">${D.kinds.map(k=>`<option>${k}</option>`).join("")}</select></div><div id="tiout"></div>`;
  return h;
};
function showTrace(){
  const out = document.getElementById("tiout"); if(!out) return;
  const v = (document.getElementById("pick").value||"").trim(); const kind = document.getElementById("kind").value;
  let id = D.records[v]?v:Object.keys(D.records).find(i=>D.records[i].name.toLowerCase()===v.toLowerCase());
  if(!id){out.innerHTML = v?`<p class="muted">No record "${esc(v)}" in this estate.</p>`:""; return;}
  const r = D.records[id]; current = id; const im = r.impact[kind];
  const order = {design_change_required:0,review_required:1,no_impact:2};
  const rows = im.rows.slice().sort((a,b)=>(order[a.classification]-order[b.classification])||String(a.level).localeCompare(String(b.level)));
  out.innerHTML = `<h3>${lvl(r.level)} ${rec(r.id,r.name)} <span class="muted">${esc(r.type)}</span></h3>
   <div class="cards"><div class="card"><b>Depends on</b> (down, towards technology)${treeHtml(r.down,true)}</div><div class="card"><b>Depended on by</b> (up, towards business)${treeHtml(r.up,true)}</div></div>
   <h3>Impact of a <b>${esc(kind)}</b></h3><p class="note">${esc(im.reason)}</p>` +
   table(["Layer","Record","Classification","Path (approved links)"], rows.map(x=>`<tr><td>${lvl(x.level)}</td><td>${rec(x.id,x.name)}</td><td class="c-${x.classification}">${esc(CLS[x.classification]||x.classification)}</td><td>${esc(x.via.join(", ")||"—")}</td></tr>`)) +
   `<p class="note">Links to supersede: ${im.supersede.length?im.supersede.map(m=>`<code>${esc(m)}</code>`).join(", "):"none"}. Classification is structural; an architect confirms before any design changes.</p>` +
   cmd(`sdem impact ${id} --change ${kind} --estate ${D.estate} --report work/impact-${id}-${kind}.md`);
}
R.matrix = () => {
  const m = D.matrix; const c = (id,n,l)=>id?`${esc(n)} <code>${esc(id)}</code>${l?` <span class="rel">(${esc(l)})</span>`:""}`:`<span class="muted">— no approved link</span>`;
  let h = `<h2>Capability → service domain → application → technology</h2><p class="note">From approved links only; each cell gives the approved link it rests on.</p>` +
    table(["Capability (A1)","Service domain (A2)","Application (A3)","Technology (A4)"], m.chain.map(r=>`<tr><td>${c(r.capability,r.capability_name)}</td><td>${c(r.domain,r.domain_name,r.links[0])}</td><td>${c(r.application,r.application_name,r.application?r.links[1]:"")}</td><td>${c(r.technology,r.technology_name,r.technology?r.links[2]:"")}</td></tr>`));
  for (const p of m.pairs) h += `<h3>${esc(p.title)}</h3>` + table([p.source,p.target], p.rows.map(r=>`<tr><td>${c(r.source,r.source_name)}</td><td>${r.targets.map(t=>`<div>${c(t.id,t.name,t.link)}</div>`).join("")}</td></tr>`));
  return h + cmd(`sdem matrix --estate ${D.estate} --md work/matrix.md`);
};
R.changes = () => {
  const C = D.changes; const last = w=>w.history[w.history.length-1];
  let h = `<h2>Changes and work</h2><p class="note">Change sets change one architecture each and are checked before they land; each produces a change event with its impact; the orchestrator (or you) plans work items from it.</p>`;
  if (C.direct_edits.length) h += `<div class="att bad">${C.direct_edits.map(esc).join("<br>")}</div>`;
  h += `<h3>Change events</h3>` + table(["Event","Layer","Change set","By","Round","Design changes in other layers","Links to supersede"], C.events.map(e=>{
    const dc = e.impact.records.filter(r=>r.classification==="design_change_required" && r.level!==e.layer && !e.impact.changed.includes(r.id));
    return `<tr><td><code>${esc(e.id)}</code></td><td>${lvl(e.layer)}</td><td><code>${esc(e.change_set)}</code></td><td>${esc(e.agent)}<div class="muted">${esc(e.person)}</div></td><td>${e.round}</td>
    <td>${dc.map(r=>`<div>${lvl(r.level)} ${rec(r.id,r.name)}</div>`).join("")||'<span class="muted">none</span>'}</td><td>${e.impact.mappings_to_supersede.map(m=>`<code>${esc(m)}</code>`).join(" ")}</td></tr>`;}));
  h += `<h3>Work items</h3>` + table(["Work item","Layer","Records","Action","Status","History"], C.work.map(w=>`<tr><td><code>${esc(w.id)}</code></td><td>${lvl(w.layer)}</td><td>${w.records.map(esc).join(", ")}</td><td>${esc(w.action)}</td><td><b>${esc(last(w).status)}</b></td>
    <td><details><summary>${w.history.length} step(s)</summary>${w.history.map(s=>`<div class="muted">${esc(s.status)} · ${esc(s.agent)} · ${esc(s.person)} · ${esc(s.at)}${s.note?" · "+esc(s.note):""}</div>`).join("")}</details></td></tr>`));
  h += `<h3>Change sets</h3>` + table(["Change set","Layer","Reason","Changes","By"], C.change_sets.map(c=>`<tr><td><code>${esc(c.id)}</code>${c.reverts?`<div class="warn">reverts ${esc(c.reverts)}</div>`:""}${c.adopted?`<div class="warn">adopted hand edit</div>`:""}</td><td>${lvl(c.layer)}</td><td>${esc(c.reason)}</td><td>${c.changes}</td><td>${esc(c.agent)}<div class="muted">${esc(c.person)}</div></td></tr>`));
  return h + cmd(`sdem events --estate ${D.estate} --open`);
};
R.aid = () => {
  const A = D.aid;
  if (!A) return `<h2>AID plans</h2><p class="note">No projection was given. Project the layers you do not have, then regenerate this page with it:</p>` + cmd(`sdem aid project --have ${D.estate}/a1-business.json --catalogue <bian-catalogue.json> --out work/prj`) + cmd(`sdem dashboard --estate ${D.estate} --projection work/prj -o work/dashboard.html`);
  let h = `<h2>AID plan ${esc(A.id)} — ${esc(A.mode)}</h2><p class="note">A projected design is a plan, never real data (ids start PRJ-; confidence at most 0.6). Projected from: ${A.have.map(esc).join(", ")}. Check: ${A.valid?'<span class="ok">valid</span>':`<span class="bad">${A.issues.length} issue(s)</span>`}.</p>`;
  if (A.ends.length) h += `<p class="note">Where AID stopped: ${A.ends.map(esc).join(" · ")}</p>`;
  h += `<h3>Against the real design</h3>` + table(["Measure","Projected","Real","Matched","Precision","Recall"], Object.entries(A.metrics).map(([k,v])=>`<tr><td>${esc(k)}</td><td>${v.projected??""}</td><td>${v.real??v.compared??""}</td><td>${v.matched??""}</td><td>${v.precision??"—"}</td><td>${v.recall??"—"}</td></tr>`));
  h += `<h3>Projected elements</h3>` + table(["Layer","Element","Step","Rule — source","Why","Confidence"], A.elements.filter(e=>!["A2.ServiceOperation","A2.BusinessObject","A2.ControlRecord","A2.ServiceGroup","A2.AssetType","A2.BehaviorQualifier","A2.BusinessObjectAttribute"].includes(e.type)).map(e=>`<tr><td>${lvl(e.level)}</td><td>${rec(e.id,e.name)}<div class="muted">${esc(e.type)}</div></td><td>${esc(e.step)}</td><td>${esc(e.source_reference)}</td><td>${esc(e.reasoning)}</td><td>${e.confidence}</td></tr>`));
  return h;
};
R.designs = () => {
  const G = D.designs;
  if (!G) return `<h2>Designs & gaps</h2><p class="note">This project has no onboarded designs. Past designs from Confluence come in with <code>sdem transform run</code> and <code>sdem load</code>; what does not fit an entity is kept here as gap records.</p>`;
  const st = G.by_status, n = G.open.length;
  let h = `<h2>Designs & gaps</h2><p class="note">What did not fit an architecture entity in onboarded designs — kept, not lost. <b>${n} open</b> · ${st.resolved||0} resolved · ${st.accepted||0} accepted. Resolve a gap when what it held is now in the data; accept it when it is left as it is, on purpose — your name and note are recorded.</p>`;
  if (n) {
    h += `<h3>Open gaps by kind</h3>` + table(["Kind","Open"], Object.entries(G.by_category).map(([k,v])=>`<tr><td>${esc(k)}</td><td>${v}</td></tr>`));
    h += `<h3>Open gaps</h3>` + table(["Gap","Kind","Page — where","What it holds","About","Deal with it"], G.open.map(g=>`<tr><td><code>${esc(g.id)}</code></td><td>${esc(g.category)}</td><td>${esc(g.page)}<div class="muted">${esc(g.where)}</div></td><td>${esc(g.text||"")}</td><td>${(g.about||[]).map(a=>`<code>${esc(a)}</code>`).join(" ")}</td><td>${cmd(`sdem designs resolve ${g.id} --estate ${D.estate} --person <you> --note "<now in the data: …>"`)}${cmd(`sdem designs accept ${g.id} --estate ${D.estate} --person <you> --note "<why it stays>"`)}</td></tr>`));
  }
  h += `<h3>Pages the designs came from</h3>` + table(["Page","Date","Captured","Entities","Facts"], G.documents.map(d=>`<tr><td>${d.url?`<a href="${esc(d.url)}">${esc(d.title)}</a>`:esc(d.title)}<div class="muted">${esc(d.id)}</div></td><td>${esc(d.modified||"—")}</td><td>${d.coverage?d.coverage.percent+"%":"—"}</td><td>${(d.entities||[]).length}</td><td>${Object.entries(d.facts||{}).map(([k,v])=>`${esc(k)}: ${esc(v)}`).join("<br>")}</td></tr>`));
  return h;
};
R.controls = () => {
  const C = D.controls;
  let h = `<h2>Controls</h2><p class="note">Automatic checks that enforce the metamodel. Last tested in: ${C.tested_in.map(t=>`${esc(t.example)} (${esc(t.date)})`).join(", ")}; good data must be accepted and bad data rejected.</p>`;
  h += table(["Control","Status","Area","Enforces","Runs","Last tested (good · bad)"], C.rows.map(c=>`<tr><td><b>${esc(c.id)}</b></td><td>${esc(c.status)}</td><td>${esc(c.area)}</td><td>${esc(c.control)}</td><td>${esc(c.runs)}</td><td>${esc(c.tested)}</td></tr>`));
  h += `<h3>Known gaps — rules nothing fully enforces</h3>` + table(["Gap","Not controlled","Risk"], C.gaps.map(g=>`<tr><td><b>${esc(g.id)}</b></td><td>${esc(g.not_controlled)}</td><td>${esc(g.risk)}</td></tr>`));
  return h;
};

const nav = document.getElementById("tabs"), main = document.getElementById("main");
TABS.forEach(([id,label])=>{const b=document.createElement("button");b.textContent=label;b.setAttribute("role","tab");b.dataset.tab=id;b.id="tab-"+id;nav.appendChild(b);
  const s=document.createElement("section");s.id=id;s.setAttribute("role","tabpanel");s.setAttribute("aria-labelledby","tab-"+id);s.hidden=true;s.innerHTML=R[id]();main.appendChild(s);});
function show(id){if(!document.getElementById(id))id="overview";TABS.forEach(([t])=>{document.getElementById(t).hidden=(t!==id);document.getElementById("tab-"+t).setAttribute("aria-selected",String(t===id));});
  try{history.replaceState(null,"","#"+id);}catch(e){}}
nav.addEventListener("click",e=>{const t=e.target.closest("button");if(t)show(t.dataset.tab);});
nav.addEventListener("keydown",e=>{if(e.key!=="ArrowRight"&&e.key!=="ArrowLeft")return;const i=TABS.findIndex(([t])=>!document.getElementById(t).hidden);const n=(i+(e.key==="ArrowRight"?1:TABS.length-1))%TABS.length;show(TABS[n][0]);document.getElementById("tab-"+TABS[n][0]).focus();});
document.addEventListener("click",e=>{const a=e.target.closest("[data-tab]");if(a&&a.tagName==="A"){e.preventDefault();show(a.dataset.tab);}
  const c=e.target.closest("[data-copy]");if(c){const t=c.dataset.copy;(navigator.clipboard?navigator.clipboard.writeText(t):Promise.reject()).then(()=>{c.textContent="copied";setTimeout(()=>c.textContent="copy",1200);}).catch(()=>{c.textContent="select & copy";});}});
const pick=document.getElementById("pick"),kind=document.getElementById("kind");if(pick){pick.addEventListener("input",showTrace);kind.addEventListener("change",showTrace);}
document.getElementById("theme").onclick=()=>{const r=document.documentElement;const dark=r.dataset.theme?r.dataset.theme==="dark":matchMedia("(prefers-color-scheme: dark)").matches;r.dataset.theme=dark?"light":"dark";};
show((location.hash||"#overview").slice(1));
</script></body></html>
'''


if __name__ == '__main__':
    raise SystemExit(main())
