"""Use-case example 2 — test Architecture Inference Design (AID) on the payment-initiation estate (docs/use-case-example-2.md).

Hide layers of a known estate, let AID (sdem/aid.py) project them, and compare with the hidden real layers (gap analysis).
Five runs, each checked against the expectations sealed in commit 17dbd33 before any run; the safety controls CTL-16 and
CTL-17 tested with good and bad data. Writes the evidence pack to docs/evidence/use-case-example-2/ and the results into
docs/use-case-example-2.md.
Usage: python scripts/use_case_example_2.py
"""
import copy, hashlib, json, re, shutil, subprocess, sys, tempfile
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from sdem import aid  # noqa: E402
from sdem.graph import FederatedGraph, LevelGraph  # noqa: E402
from sdem.metamodel import Metamodel  # noqa: E402
from sdem.rules_engine import RulesEngine  # noqa: E402
from sdem.store import GraphReader, build  # noqa: E402
from sdem.validate import load_registry, load_schema, validate  # noqa: E402

EST = ROOT / 'examples' / 'payment-initiation'
DOC = ROOT / 'docs' / 'use-case-example-2.md'
EVID = ROOT / 'docs' / 'evidence' / 'use-case-example-2'
LEVELS = {'A1': 'a1-business.json', 'A2': 'a2-service-domain.json', 'A3': 'a3-application.json', 'A4': 'a4-technology.json'}
RUNS = [(1, ('A1', 'A2'), 'A3, A4'), (2, ('A1',), 'A2, A3, A4'), (3, ('A4',), 'A3, A2, A1'), (4, ('A3', 'A4'), 'A2, A1'), (5, ('A1', 'A3'), 'A2')]
CREATED = '2026-10-27T00:00:00+00:00'  # fixed so the evidence is reproducible


def _j(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def empty_registry(): return {'registry_version': load_registry()['$schema_version'], 'metamodel_version': '0.4.0', 'mappings': []}


def catalogue(first='payment-initiation'):
    """The test's BIAN catalogue: the A2 layer of every example estate combined, keyed on BIAN identity (type + name) as a
    real catalogue is — the estates' ids are local, and 37 of them name different elements in different estates.
    Same type and name → one record (the first estate's id); a local id already taken by another element → `<id>@<estate>`;
    a part keeps one whole (the first estate's grouping), so the catalogue passes the dataset check."""
    inst, rels, by_key, used, parent = [], [], {}, set(), {}
    files = sorted((ROOT / 'examples').glob('*/a2-service-domain.json'), key=lambda f: (f.parent.name != first, f.parent.name))
    for f in files:
        if 'reference-structure' in str(f): continue
        d, est, local, added = _j(f), f.parent.name, {}, []
        for i in d['instances']:
            k = (i['type'], i['name'])
            if k not in by_key:
                nid = i['id'] if i['id'] not in used else f"{i['id']}@{est}"
                used.add(nid); by_key[k] = nid; added.append(dict(i, id=nid))
            local[i['id']] = by_key[k]
        fix = lambda v: [local.get(x, x) for x in v] if isinstance(v, list) else local.get(v, v) if isinstance(v, str) else v
        for x in added:
            if x.get('attributes'): x['attributes'] = {k: fix(v) for k, v in x['attributes'].items()}
        inst += added
        for r in d.get('relationships', []):
            r2 = dict(r, source=local[r['source']], target=local[r['target']])
            if r2['kind'] == 'composition':  # one whole per part, as in BIAN: the first estate's grouping is kept
                if parent.setdefault(r2['target'], r2['source']) != r2['source']: continue
            if r2 not in rels: rels.append(r2)
    ids = {i['id'] for i in inst}
    cat = {'level': 'A2', 'model_id': 'aid-test-bian-catalogue', 'model_version': 'test', 'metamodel_version': '0.4.0', 'source_system': 'combined example A2 layers',
           'instances': inst, 'relationships': [r for r in rels if r['source'] in ids and r['target'] in ids]}
    # a merged element may now have more links than the rulebook allows (LC-10): keep the earlier estate's, drop the later one
    mm, typ, dropped = Metamodel.load(), {i['id']: i['type'] for i in inst}, []
    while True:
        bad = [m for m in (re.match(r'instance (\S+): \d+ (\w+) links with (\S+), at most', x) for x in LevelGraph(cat, mm).validate()) if m]
        if not bad: break
        x, kind, other = bad[0].groups()
        r = [r for r in cat['relationships'] if r['kind'] == kind and x in (r['source'], r['target']) and mm.is_a(typ[r['target'] if r['source'] == x else r['source']], other)][-1]
        cat['relationships'].remove(r); dropped.append(r)
    catalogue.dropped = dropped
    return cat


def _ids(pkg, lvl, t=None): return {i['id'] for i in pkg['layers'].get(lvl, {'instances': []})['instances'] if t is None or i['type'] == t}
def _confs(pkg, lvl): return [i['projection']['confidence'] for i in pkg['layers'].get(lvl, {'instances': []})['instances']]


def expectations(n, pkg, g, real, reg, results):
    """The sealed expectations (docs/use-case-example-2.md, commit 17dbd33), as checks on run n."""
    M = g['metrics']; approved = [m for m in reg['mappings'] if m['status'] == 'approved']
    ops = {i['id']: i for i in real['A2']['instances'] if i['type'] == 'A2.ServiceOperation'}
    run = aid.Run(aid._reader({'A2': real['A2']}, Metamodel.load()), 'UCE2')
    dom_of = {o: run.domain_of(o)['id'] for o in ops if run.domain_of(o)}
    if n == 1:
        doms = {dom_of[o] for o in ops if o in dom_of}; api = M.get('A3 APIs (method and path)', {})
        a4 = pkg['layers'].get('A4', {'instances': []})['instances']
        return [(f'every service domain with operations gets a projected component — {sorted(doms)}', bool(doms) and all(f'PRJ-APP-{d}' in _ids(pkg, 'A3') for d in doms)),
                ('every operation with a REST form gets a projected API', all(f'PRJ-API-{o}' in _ids(pkg, 'A3') for o, i in ops.items() if i['attributes'].get('action_term') != 'Notify')),
                ('no platform, environment or network invented', all(i['type'] == 'A4.Deployment' and not {'platform_id', 'environment_id'} & set(i.get('attributes') or {}) for i in a4)),
                (f"APIs match the real method and path for at least 2 — {api.get('matched')} of {api.get('compared')}", api.get('matched', 0) >= 2),
                (f"higher than the baseline (2) after the qualifier fix AID-Q04 — {api.get('matched')}", api.get('matched', 0) > 2)]
    if n == 2:
        named = {dom_of[o] for i in real['A1']['instances'] for o in (i.get('attributes') or {}).get('invokes', []) if o in dom_of}
        m = M.get('A2 service domains (those the real design links)', {})
        return [(f"all real service domains found where the business names its operations — {sorted(named)}", bool(named) and named <= _ids(pkg, 'A2', 'A2.ServiceDomain')),
                (f"few wrong — precision {m.get('precision')}", (m.get('precision') or 0) >= 0.5)]
    if n == 3:
        m = M.get('A3 components (named by A4)', {})
        return [(f"every application the technology names is projected — recall {m.get('recall')}", m.get('recall') == 1.0),
                ('BIAN domains suggested at low confidence', bool(_confs(pkg, 'A2')) and max(_confs(pkg, 'A2')) <= aid.LOW),
                ('the business layer marked the weakest (low)', bool(_confs(pkg, 'A1')) and max(_confs(pkg, 'A1')) <= aid.LOW)]
    if n == 4:
        impl = {m['source']['id'] for m in approved if m['relationship'] == 'IMPLEMENTED_BY'}
        want = {dom_of[o] for o in impl if o in dom_of}
        return [(f"BIAN domains correct where the APIs carry BIAN-style operations — {sorted(want)}", bool(want) and want <= _ids(pkg, 'A2', 'A2.ServiceDomain'))]
    if n == 5:
        p5 = M.get('A2 service domains (those the real design links)', {}).get('precision') or 0
        p2 = next(r for r in results if r['run'] == 2)['metrics'].get('A2 service domains (those the real design links)', {}).get('precision') or 0
        return [(f'at least as accurate as run 2 — precision {p5} vs {p2}', p5 >= p2)]


def safety(real, packages, cat):
    """CTL-16 and CTL-17, each with good data (must be accepted) and bad data (must be rejected) — as in example 1."""
    mm = Metamodel.load(); rows = []; tmp = Path(tempfile.mkdtemp(prefix='uce2s-'))
    def fed_errors(levels):
        return [i for v in FederatedGraph([LevelGraph(x, mm) for x in levels], [aid._registry()], mm).check().values() for i in v]
    try:
        p1 = packages[1]; prj = next(i for i in p1['layers']['A3']['instances'] if i['id'].startswith('PRJ-APP-'))
        # CTL-16 — kept apart
        rows.append(('CTL-16', 'good', 'the real datasets load as real data', fed_errors([real[l] for l in LEVELS]), False))
        bad = copy.deepcopy(real['A3']); bad['instances'].append({k: v for k, v in prj.items() if k != 'projection'})
        rows.append(('CTL-16', 'bad', f"put the projected component {prj['id']} into the real A3 dataset", fed_errors([real['A1'], real['A2'], bad, real['A4']]), True))
        dsn = RulesEngine().infer(aid._reader({'A1': real['A1'], 'A2': real['A2']}, mm), {'id': 'UCE2'}).get('design', [])
        bad = copy.deepcopy(real['A3']); bad['instances'].append(next(x for x in dsn if x['level'] == 'A3')['instances'][0])
        rows.append(('CTL-16', 'bad', "put a design-mode record (`DSN-`) into the real A3 dataset", fed_errors([real['A1'], real['A2'], bad, real['A4']]), True))
        link = {k: v for k, v in p1['links']['links'][0].items() if k != 'projection'}
        link.update(status='approved', reviewer_id='ROLE-ARCH-REVIEWER', approved_at='2026-10-27T00:00:00Z', evidence=['projection:PRJ-A1-A2'])
        reg = {'registry_version': load_registry()['$schema_version'], 'metamodel_version': mm.version, 'mappings': [link]}
        errs = [e for e in validate(reg, load_registry(), load_schema(), metamodel=mm) if 'CTL-16' in e]
        rows.append(('CTL-16', 'bad', f"approve the projected link {link['mapping_id']} in a registry", errs, True))
        for lvl in ('A3',):
            f = tmp / f'p-{lvl}.json'; f.write_text(json.dumps(p1['layers'][lvl]), encoding='utf-8')
            rf = tmp / 'r.json'; rf.write_text(json.dumps(aid._registry()), encoding='utf-8')
            fa = tmp / 'a1.json'; fa.write_text(json.dumps(real['A1']), encoding='utf-8')
            e = build([str(fa), str(f), str(rf)], tmp / 'store')
            rows.append(('CTL-16', 'bad', 'load a projected layer into a graph store of real data', e['errors'] if e['result'] == 'rejected' else [], True))
        # CTL-17 — marked, capped, BIAN not invented
        for n, pkg in sorted(packages.items()):
            rows.append(('CTL-17', 'good', f'run {n} projection package', aid.check(pkg, cat), False))
        tamper = [('remove the provenance of a projected record', lambda p: p['layers']['A3']['instances'][0].pop('projection')),
                  ('raise a projected record to 0.9 confidence', lambda p: p['layers']['A3']['instances'][0]['projection'].update(confidence=0.9)),
                  ('add a BIAN service domain not in the catalogue', lambda p: p['layers'].setdefault('A2', {'instances': []})['instances'].append({'id': 'SD-INVENTED', 'type': 'A2.ServiceDomain', 'version': '1.0', 'name': 'Invented', 'projection': {'step': 'F1', 'rule': aid.CATALOGUE_RULE, 'inferred_from': [], 'reasoning': 'x', 'confidence': 0.4}})),
                  ('drop the `PRJ-` mark from a projected component', lambda p: p['layers']['A3']['instances'][0].update(id='APP-LOOKS-REAL')),
                  ('set a projected link to approved', lambda p: p['links']['links'][0].update(status='approved'))]
        for what, f in tamper:
            p = copy.deepcopy(p1); f(p); rows.append(('CTL-17', 'bad', what, aid.check(p, cat), True))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    out = []
    for ctl, kind, test, errs, should_reject in rows:
        ok = bool(errs) == should_reject
        out.append({'control': ctl, 'data': kind, 'test': test, 'should': 'rejected' if should_reject else 'accepted', 'did': 'rejected' if errs else 'accepted',
                    'message': (errs[0] if errs else '—'), 'pass': ok})
    return out


def run():
    R = {'date': date.today().isoformat(), 'runs': [], 'safety': [], 'findings': [], 'evidence': {}}; E = R['evidence']
    real = {lvl: _j(EST / f) for lvl, f in LEVELS.items()}; reg = _j(EST / 'mappings.json'); cat = catalogue()
    E['catalogue-summary.json'] = {'service_domains': sorted(f"{i['id']}: {i['name']}" for i in cat['instances'] if i['type'] == 'A2.ServiceDomain'),
                                   'records': len(cat['instances']), 'sha256': aid._sha(cat),
                                   'links_dropped_on_merge (LC-10: kept the earlier estate\'s)': catalogue.dropped}
    packages = {}
    for n, has, proj in RUNS:
        pkg = aid.project({l: real[l] for l in has}, cat, pid=f'PRJ-RUN{n}', created_at=CREATED); packages[n] = pkg
        hidden = {l: real[l] for l in LEVELS}
        g = aid.gaps(pkg, hidden, reg)
        r = {'run': n, 'has': ' + '.join(has), 'projects': proj, 'metrics': g['metrics'], 'rows': g['rows'], 'ends': g['projection_ends'],
             'records': {l: s['records'] for l, s in pkg['projection']['summary'].items()}, 'links': pkg['projection']['links']}
        r['checks'] = expectations(n, pkg, g, real, reg, R['runs'])
        R['runs'].append(r)
        E[f'run{n}-projection.json'] = pkg; E[f'run{n}-gaps.json'] = g
    R['safety'] = safety(real, packages, cat)
    mark = lambda xs: ('✅' if all(x['pass'] for x in xs) else '❌') if xs else '—'
    R['controls'] = [{'id': c, 'good': mark([s for s in R['safety'] if s['control'] == c and s['data'] == 'good']),
                      'bad': mark([s for s in R['safety'] if s['control'] == c and s['data'] == 'bad'])} for c in ('CTL-16', 'CTL-17')]
    R['findings'] = [
        {'id': 'AID-B1', 'what': 'design mode marked projections `DSN-` + `planned` only', 'action': 'closed — AID marks `PRJ-` with a `projection` object on every element (CTL-17)'},
        {'id': 'AID-B2', 'what': 'the example estates use local ids: 37 A2 ids name different elements in different estates (e.g. `SD-CA` is Current Account in one, Credit Assessment in another)', 'action': 'the test catalogue merges by BIAN type + name and qualifies clashes (`SD-CA@digital-lending`); a real catalogue keys on BIAN canonical identity'},
        {'id': 'AID-B3', 'what': 'from A4 alone an application is known only by its id; domains come from id words (`PAY` → Payment …)', 'action': 'kept low; the weakest evidence R2 accepts — expect "projected only" domains'},
        {'id': 'AID-B4', 'what': 'the projection schema (AID-O05) and the view/trace PROJECTED label (AID-O06) are not built', 'action': 'next AID build items'}]
    return R


def write_evidence(R):
    if EVID.exists(): shutil.rmtree(EVID)
    EVID.mkdir(parents=True); files = {}
    for name, obj in list(R['evidence'].items()) + [('results.json', {k: v for k, v in R.items() if k != 'evidence'})]:
        text = json.dumps(obj, indent=2, ensure_ascii=False, default=str) + '\n'; (EVID / name).write_text(text, encoding='utf-8'); files[name] = hashlib.sha256(text.encode('utf-8')).hexdigest()
    m = {'example': 'use-case-example-2', 'run_date': R['date'], 'code_commit': subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=ROOT, capture_output=True, text=True).stdout.strip(), 'files': files}
    (EVID / 'manifest.json').write_text(json.dumps(m, indent=2) + '\n', encoding='utf-8')


def render(R):
    mark = {'matched': '✅', 'differs': '≠', 'projected only': '➕', 'real only': '➖'}
    allok = all(ok for r in R['runs'] for _, ok in r['checks']); safe = all(s['pass'] for s in R['safety'])
    nchk = sum(len(r['checks']) for r in R['runs']); npass = sum(ok for r in R['runs'] for _, ok in r['checks'])
    out = [f"## Results — run {R['date']} (AID built)", '',
           f"**Verdict:** {npass} of {nchk} sealed expectations met across the five runs; safety controls {sum(s['pass'] for s in R['safety'])} of {len(R['safety'])} tests pass"
           + (' — every projection stayed apart, marked and capped.' if safe else ' — **a safety test failed**.'), '',
           'Generated by `python scripts/use_case_example_2.py` with `sdem/aid.py`; evidence in [`evidence/use-case-example-2/`](evidence/use-case-example-2/manifest.json). '
           'The baseline before AID was built is kept below for comparison.', '',
           '| Run | Has | Projects | Projected records | Expectations met | Key measure |', '|---|---|---|---|---|---|']
    for r in R['runs']:
        key = '; '.join(f"{k.split(' (')[0]}: P {v['precision']} / R {v['recall']}" for k, v in r['metrics'].items() if 'precision' in v and not k.startswith('links'))
        api = r['metrics'].get('A3 APIs (method and path)')
        if api: key += f"; APIs {api['matched']} of {api['compared']} match"
        out.append(f"| {r['run']} | {r['has']} | {r['projects']} | {', '.join(f'{l} {c}' for l, c in r['records'].items())} | {sum(ok for _, ok in r['checks'])} of {len(r['checks'])} | {key} |")
    out += ['', 'P = precision (how much of what AID projected is real) · R = recall (how much of the real design AID found).']
    for r in R['runs']:
        out += ['', f"### Run {r['run']} — has {r['has']}, projects {r['projects']}", '', '| Sealed expectation | Met |', '|---|---|']
        out += [f"| {c} | {'✅' if ok else '❌'} |" for c, ok in r['checks']]
        out += ['', '| Measure | Projected | Real | Matched | Precision | Recall |', '|---|---|---|---|---|---|']
        for k, v in r['metrics'].items():
            if 'compared' in v: out.append(f"| {k} | {v['compared']} | {v['compared']} | {v['matched']} | — | — |")
            else: out.append(f"| {k} | {v['projected']} | {v['real']} | {v['matched']} | {v['precision']} | {v['recall']} |")
        rows = [x for x in r['rows'] if x['result'] != 'matched' or x['layer'] == 'A3 APIs']
        if rows:
            out += ['', '<details><summary>Gap analysis — differences and API matches</summary>', '', '| Layer | Element | Result |', '|---|---|---|']
            out += [f"| {x['layer']} | {x['element']} | {mark.get(x['result'], '')} {x['result']} |" for x in rows] + ['', '</details>']
        if r['ends']: out += ['', 'Notes: ' + ' · '.join(r['ends'])]
    out += ['', '### Safety controls — good and bad data', '', '| Control | Data | Test | Should | Did | Message | Pass |', '|---|---|---|---|---|---|---|']
    out += [f"| {s['control']} | {s['data']} | {s['test']} | {s['should']} | {s['did']} | {s['message'][:140]} | {'✅' if s['pass'] else '❌'} |" for s in R['safety']]
    out += ['', '### Findings', '', '| ID | What | Action |', '|---|---|---|'] + [f"| {f['id']} | {f['what']} | {f['action']} |" for f in R['findings']]
    return '\n'.join(out) + '\n'


BASELINE = '## Baseline before AID was built'


def main():
    R = run(); write_evidence(R); text = DOC.read_text(encoding='utf-8')
    text = text.replace('## Results — baseline run', f'{BASELINE} — run', 1)  # first run after the build: keep the baseline, retitled
    plan = text[:min(i for i in (text.find('## Results — run'), text.find(BASELINE), len(text)) if i >= 0)]
    base = text[text.index(BASELINE):] if BASELINE in text else ''
    text = plan.rstrip('\n') + '\n\n' + render(R) + ('\n' + base if base else '')
    text = text.replace('> **Status: baseline run 2026-10-27 — expected results sealed before the run (commit 17dbd33).**',
                        f"> **Status: AID built and run {R['date']} — expected results sealed before any run (commit 17dbd33); the baseline is kept at the end.**")
    DOC.write_text(text.rstrip('\n') + '\n', encoding='utf-8')
    print(render(R).split('\n')[2])
    return 0 if all(ok for r in R['runs'] for _, ok in r['checks']) and all(s['pass'] for s in R['safety']) else 1


if __name__ == '__main__':
    raise SystemExit(main())
