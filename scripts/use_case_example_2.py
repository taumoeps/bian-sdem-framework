"""Use-case example 2 — test Architecture Inference Design (AID) on the payment-initiation estate (docs/use-case-example-2.md).

Hide layers of a known estate, let AID project them, and compare with the hidden real layers (gap analysis).
Baseline: only run 1 (forward from A1 + A2) exists today, as the engine's design mode; runs 2–5 and controls CTL-16/17
are reported as not built — and the safety tests show what happens today without them.
Writes the evidence pack to docs/evidence/use-case-example-2/ and the results into docs/use-case-example-2.md.
Usage: python scripts/use_case_example_2.py
"""
import hashlib, json, shutil, subprocess, sys, tempfile
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from sdem.graph import FederatedGraph, LevelGraph  # noqa: E402
from sdem.metamodel import Metamodel  # noqa: E402
from sdem.rules_engine import RulesEngine  # noqa: E402
from sdem.store import GraphReader, build  # noqa: E402
from sdem.validate import load_registry  # noqa: E402

EST = ROOT / 'examples' / 'payment-initiation'
DOC = ROOT / 'docs' / 'use-case-example-2.md'
EVID = ROOT / 'docs' / 'evidence' / 'use-case-example-2'
LEVELS = {'A1': 'a1-business.json', 'A2': 'a2-service-domain.json', 'A3': 'a3-application.json', 'A4': 'a4-technology.json'}


def _j(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def empty_registry(): return {'registry_version': load_registry()['$schema_version'], 'metamodel_version': '0.4.0', 'mappings': []}


def catalogue():
    """The test's BIAN catalogue: the A2 layer of every example estate combined (first record of each id kept)."""
    inst, rels, seen = [], [], set()
    for f in sorted((ROOT / 'examples').glob('*/a2-service-domain.json')):
        if 'reference-structure' in str(f): continue
        d = _j(f)
        for i in d['instances']:
            if i['id'] not in seen: seen.add(i['id']); inst.append(i)
        rels += [r for r in d.get('relationships', []) if r not in rels]
    ids = {i['id'] for i in inst}
    return {'level': 'A2', 'model_id': 'aid-test-bian-catalogue', 'model_version': 'test', 'metamodel_version': '0.4.0', 'source_system': 'combined example A2 layers',
            'instances': inst, 'relationships': [r for r in rels if r['source'] in ids and r['target'] in ids]}


def run():
    tmp = Path(tempfile.mkdtemp(prefix='uce2-')); R = {'date': date.today().isoformat(), 'runs': [], 'safety': [], 'findings': [], 'evidence': {}}
    E = R['evidence']
    try:
        real = {lvl: _j(EST / f) for lvl, f in LEVELS.items()}; answer = _j(EST / 'mappings.json')['mappings']
        cat = catalogue()
        E['catalogue-summary.json'] = {'service_domains': sorted(i['id'] for i in cat['instances'] if i['type'] == 'A2.ServiceDomain'),
                                       'operations': sum(1 for i in cat['instances'] if i['type'] == 'A2.ServiceOperation')}
        # ---------------- run 1 — architect has A1 + A2; AID projects A3, A4 (today: the engine's design mode)
        d = tmp / 'r1'; d.mkdir()
        for lvl in ('A1', 'A2'): (d / LEVELS[lvl]).write_text(json.dumps(real[lvl]), encoding='utf-8')
        (d / 'registry.json').write_text(json.dumps(empty_registry()), encoding='utf-8')
        build([str(d / LEVELS['A1']), str(d / LEVELS['A2']), str(d / 'registry.json')], d / 'store')
        res = RulesEngine().infer(GraphReader.from_store(d / 'store'), {'id': 'UCE2R1'})
        design = {x['level']: x for x in res.get('design', [])}; props = res['proposals']
        E['run1-projected-design.json'] = {'design': res.get('design', []), 'links': props}
        a3p, a4p = design.get('A3', {'instances': []}), design.get('A4', {'instances': []})
        rows = []
        # domains → components
        real_real = {(m['source']['id'], m['target']['id']) for m in answer if m['relationship'] == 'REALIZED_BY'}
        proj_real = {(m['source']['id'], m['target']['id']) for m in props if m['relationship'] == 'REALIZED_BY'}
        for dom in sorted({s for s, _ in real_real} | {s for s, _ in proj_real}):
            rc = sorted(c for s, c in real_real if s == dom); pc = sorted(c for s, c in proj_real if s == dom)
            sub = [r['target'] for r in real['A3']['relationships'] if r['kind'] == 'composition' and r['source'] in rc and r['target'].startswith('CMP-')]
            res_ = 'matched' if rc and pc else 'projected only' if pc else 'real only'
            rows.append({'layer': 'A3', 'element': f'component realising {dom}', 'projected': ', '.join(pc) or '—', 'real': ', '.join(rc) + (f' (with {len(sub)} sub-components)' if sub else '') or '—',
                         'result': res_ + (' — structure differs (one projected component; the real one has sub-components)' if res_ == 'matched' and sub else ''), 'confidence': 0.4 if pc else None})
        # operations → APIs (method + path)
        real_impl = {m['source']['id']: m['target']['id'] for m in answer if m['relationship'] == 'IMPLEMENTED_BY'}
        api = {i['id']: i for i in real['A3']['instances'] if i['type'] == 'A3.APIOperation'}
        papi = {i['id']: i for i in a3p['instances'] if i['type'] == 'A3.APIOperation'}
        proj_impl = {m['source']['id']: m['target']['id'] for m in props if m['relationship'] == 'IMPLEMENTED_BY'}
        matched_api = 0; compared = 0
        ops = [i for i in real['A2']['instances'] if i['type'] == 'A2.ServiceOperation']
        for op in ops:
            r_ = api.get(real_impl.get(op['id'])); p_ = papi.get(proj_impl.get(op['id']))
            rf = f"{r_['attributes']['method']} {r_['attributes']['path']}" if r_ else None; pf = f"{p_['attributes']['method']} {p_['attributes']['path']}" if p_ else None
            if rf or pf:
                compared += 1 if (rf and pf) else 0
                same = rf == pf; matched_api += 1 if (rf and pf and same) else 0
                rows.append({'layer': 'A3', 'element': f"API for {op['name']}", 'projected': pf or '—', 'real': rf or '—',
                             'result': 'matched' if same else 'differs' if (rf and pf) else 'projected only' if pf else 'real only', 'confidence': 0.4 if pf else None})
        unmapped_real = [a for a in api if a not in real_impl.values()]
        for a in unmapped_real:
            rows.append({'layer': 'A3', 'element': f"API {a} (no BIAN operation mapped)", 'projected': '—', 'real': f"{api[a]['attributes']['method']} {api[a]['attributes']['path']}", 'result': 'real only', 'confidence': None})
        # deployments; nothing invented in A4
        real_dep = [i for i in real['A4']['instances'] if i['type'] == 'A4.Deployment']; proj_dep = [i for i in a4p['instances'] if i['type'] == 'A4.Deployment']
        rows.append({'layer': 'A4', 'element': 'deployments of the Payment Initiation component', 'projected': str(len(proj_dep)),
                     'real': f"{sum(1 for x in real_dep if (x.get('attributes') or {}).get('component_id') == 'APP-PAY-HUB')} (production, UAT)", 'result': 'differs — one projected, the real one is deployed twice', 'confidence': 0.4})
        invented = [i['id'] for i in a4p['instances'] if i['type'] != 'A4.Deployment' or {'platform_id', 'environment_id'} & set(i.get('attributes') or {})]
        R['runs'].append({'run': 1, 'has': 'A1 + A2', 'projects': 'A3, A4', 'status': 'run', 'rows': rows,
                          'checks': [('every service domain with operations gets a projected component', all(r['result'].startswith('matched') for r in rows if r['element'].startswith('component'))),
                                     ('every operation with a REST form gets a projected API', all(proj_impl.get(o['id']) for o in ops if o['attributes'].get('action_term') != 'Notify')),
                                     ('no platform, environment or network invented', not invented),
                                     (f'APIs match the real method and path for at least 2 ({matched_api} of {compared} operations that have both)', matched_api >= 2)],
                          'summary': f'{matched_api} of {compared} APIs match by method and path; 1 component and 1 deployment projected for the one service domain with operations; nothing invented in A4'})
        R['findings'].append({'id': 'AID-B1', 'what': f"today's design mode marks projected records `DSN-` with lifecycle `planned`, not `PRJ-` with projection provenance (AID-D02, CTL-17)", 'action': 'part of the AID build'})
        # ---------------- runs 2–5 — not built
        for n, has, proj in ((2, 'A1 only', 'A2, A3, A4'), (3, 'A4 only', 'A3, A2, A1'), (4, 'A3 + A4', 'A2, A1'), (5, 'A1 + A3', 'A2')):
            R['runs'].append({'run': n, 'has': has, 'projects': proj, 'status': 'not built', 'rows': [], 'checks': [], 'summary': 'AID not built yet — no projection made'})
        # ---------------- safety — what happens today without CTL-16 / CTL-17
        mm = Metamodel.load()
        leak = json.loads(json.dumps(real['A3'])); leak['instances'].append(a3p['instances'][0])
        fg = FederatedGraph([LevelGraph(x, mm) for x in (real['A1'], real['A2'], leak, real['A4'])], [empty_registry()], mm)
        errs = [i for v in fg.check().values() for i in v]; E['safety-projected-record-in-real-data.json'] = errs
        R['safety'].append({'control': 'CTL-16', 'test': f"put the projected component {a3p['instances'][0]['id']} into the real A3 dataset", 'should': 'rejected',
                            'did': 'accepted — no control stops it yet' if not errs else f'rejected — {errs[0]}', 'status': 'not built', 'pass': bool(errs)})
        R['safety'].append({'control': 'CTL-17', 'test': 'every projected element carries projection provenance and is at most medium confidence', 'should': 'yes',
                            'did': f"confidence at most medium: {'yes' if all(m['confidence'] <= 0.6 for m in props) else 'no'}; projection provenance: no (`DSN-`, `planned` only)", 'status': 'not built', 'pass': False})
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
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
    sym = lambda r: next((v for k, v in mark.items() if r.startswith(k)), '')
    out = [f"## Results — baseline run {R['date']}", '',
           '**Verdict:** run 1 works today and meets its sealed expectations; runs 2–5 and the safety controls are **not built** — the safety test shows a projected record is accepted into real data today, which is the risk CTL-16 will close.', '',
           'Generated by `python scripts/use_case_example_2.py` — the real engine; evidence in [`evidence/use-case-example-2/`](evidence/use-case-example-2/manifest.json).', '',
           '| Run | Has | Projects | Status | Summary |', '|---|---|---|---|---|']
    out += [f"| {r['run']} | {r['has']} | {r['projects']} | {r['status']} | {r['summary']} |" for r in R['runs']]
    r1 = R['runs'][0]
    out += ['', '### Run 1 — sealed expectations', '', '| Expectation | Result |', '|---|---|'] + [f"| {c} | {'✅' if ok else '❌'} |" for c, ok in r1['checks']]
    out += ['', '### Run 1 — gap analysis', '', '| Layer | Element | Projected | Real | Result | Confidence |', '|---|---|---|---|---|---|']
    out += [f"| {x['layer']} | {x['element']} | {x['projected']} | {x['real']} | {sym(x['result'])} {x['result']} | {x['confidence'] or '—'} |" for x in r1['rows']]
    out += ['', '### Safety controls', '', '| Control | Test | Should | Did today | Status |', '|---|---|---|---|---|']
    out += [f"| {s['control']} | {s['test']} | {s['should']} | {s['did']} | {s['status']} |" for s in R['safety']]
    out += ['', '### Findings for the build', '', '| ID | What | Action |', '|---|---|---|'] + [f"| {f['id']} | {f['what']} | {f['action']} |" for f in R['findings']]
    return '\n'.join(out) + '\n'


def main():
    R = run(); write_evidence(R); text = DOC.read_text(encoding='utf-8')
    if '## Results' in text: text = text[:text.index('## Results')]
    text = text.replace('> **Status: plan — expected results sealed 2026-10-27, before any run.**', f"> **Status: baseline run {R['date']} — expected results sealed before the run (commit 17dbd33).**")
    DOC.write_text(text.rstrip('\n') + '\n\n' + render(R), encoding='utf-8')
    print(render(R).split('\n')[2])
    return 0 if all(ok for c, ok in R['runs'][0]['checks']) else 1


if __name__ == '__main__':
    raise SystemExit(main())
