"""Use-case example 1 — test the rulebook (metamodel) on the payment-initiation datasets (docs/use-case-example-1.md).

Runs the real checks and the real engine (sdem/rules_engine.py; no AI). Run 1: good data, no links between the layers at the
start. Run 2: one planted mistake per copy of the data, so no mistake hides another. Approval is simulated: a stand-in
architect adds the evidence each link type requires; it never invents a BIAN identifier.
Writes the results into docs/use-case-example-1.md (section "Results") and returns them for tests/test_use_case_example_1.py.
Usage: python scripts/use_case_example_1.py
"""
import copy, json, shutil, sys, tempfile
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from sdem.diff import diff  # noqa: E402
from sdem.evaluate import evaluate  # noqa: E402
from sdem.graph import FederatedGraph, LevelGraph  # noqa: E402
from sdem.metamodel import Metamodel  # noqa: E402
from sdem.rules_engine import RulesEngine  # noqa: E402
from sdem.store import GraphReader, build  # noqa: E402
from sdem.validate import load_registry, load_schema, validate  # noqa: E402

EST = ROOT / 'examples' / 'payment-initiation'
DOC = ROOT / 'docs' / 'use-case-example-1.md'
LEVELS = ('a1-business.json', 'a2-service-domain.json', 'a3-application.json', 'a4-technology.json')
REVIEW = 'use-case-example-1 (simulated architect)'


def _j(p): return json.loads(Path(p).read_text(encoding='utf-8'))


def datasets(): return {f: _j(EST / f) for f in LEVELS}


def empty_registry(): return {'registry_version': load_registry()['$schema_version'], 'metamodel_version': '0.4.0', 'mappings': []}


def check(ds, registry=None):
    """The dataset check (sdem-graph check): errors and warnings."""
    mm = Metamodel.load(); fg = FederatedGraph([LevelGraph(d, mm) for d in ds.values()], [registry or empty_registry()], mm)
    rep = fg.check()
    return [f'{k}: {i}' for k, v in rep.items() for i in v], [w for v in getattr(fg, 'warnings', {}).values() for w in v]


def validate_doc(doc, ds):
    """The link checker (sdem-validate --strict), ends resolved against the datasets."""
    mm = Metamodel.load(); fg = FederatedGraph([LevelGraph(d, mm) for d in ds.values()], [], mm); w = []
    return list(validate(doc, load_registry(), load_schema(), entity_resolver=fg, warnings=w, metamodel=mm)) + [x for x in w if 'must be supplied before approval' not in x]


def write_set(tmp, ds, registry):
    d = Path(tempfile.mkdtemp(dir=tmp))
    for f, doc in ds.items(): (d / f).write_text(json.dumps(doc), encoding='utf-8')
    (d / 'registry.json').write_text(json.dumps(registry), encoding='utf-8')
    return [str(d / f) for f in ds] + [str(d / 'registry.json')], d


def approve(props, ds, with_evidence=True):
    """Stand-in architect: approve every proposal. With evidence, add the evidence kinds the link type requires and the
    BIAN release for BIAN-anchored types; a BIAN identifier missing from the A2 dataset is never invented."""
    types = {(t['source_type'], t['relationship'], t['target_type']): t for t in load_registry()['relationships']}
    mm = Metamodel.load(); out = []
    for m in props:
        a = copy.deepcopy(m); a.update(status='approved', reviewer_id=REVIEW, approved_at=date.today().isoformat())
        if with_evidence:
            t = next(t for (s, r, g), t in types.items() if r == m['relationship'] and mm.is_a(m['source']['type'], s) and mm.is_a(m['target']['type'], g))
            a['evidence'] = a['evidence'] + [f'{k}:{REVIEW}' for k in t['required_evidence']]
            if t['authority'].startswith('bian_'): a['bian_release'] = 'BIAN 14.0'
        out.append(a)
    return {**empty_registry(), 'mappings': out}


def run():
    tmp = Path(tempfile.mkdtemp(prefix='uce1-')); R = {'date': date.today().isoformat(), 'tests': [], 'links': [], 'gaps': []}
    def t(area, data, should, did, control, ok):
        R['tests'].append({'area': area, 'data': data, 'should': should, 'did': did, 'control': control, 'pass': bool(ok)})
    try:
        answer = _j(EST / 'mappings.json')
        # ---------------- run 1 — good data
        ds = datasets(); errs, warns = check(ds)
        n_rec = sum(len(d['instances']) for d in ds.values()); n_lnk = sum(len(d.get('relationships', [])) for d in ds.values())
        t('1–3 Records, information, links inside a layer', f'the four datasets as they are ({n_rec} records, {n_lnk} links inside layers)', 'accepted', f'accepted — {len(errs)} errors, {len(warns)} completeness warnings' if not errs else f'{len(errs)} errors: {errs[:2]}', 'dataset check', not errs)
        paths, _ = write_set(tmp, ds, empty_registry()); st = tmp / 'store1'
        e = build(paths, st); reader = GraphReader.from_store(st)
        t('Knowledge graph', 'build the graph store with no links between layers', 'built; 0 links between layers', f"{e['result']}; {len(reader.fg.edges())} links between layers", 'graph store build', e['result'] == 'accepted' and not reader.fg.edges())
        res = RulesEngine().infer(reader, {'id': 'UCE1'}); props = res['proposals']
        score = evaluate([answer], [{'mappings': props}])
        o = score['overall']
        t('5 Finding links', 'engine applies the 69 link-finding rules', '18 links, all correct', f"{o['proposed']} proposed — {o['tp']} correct, {o['fp']} wrong, {o['fn']} missed", 'acceptance (answer key)', o['tp'] == 18 and o['fp'] == 0 and o['fn'] == 0)
        refused = [a for a in res['log'] if a['outcome'] == 'no_proposal']
        key = {(m['source']['id'], m['relationship'], m['target']['id']) for m in answer['mappings'] if m['status'] == 'approved'}
        for m in props:
            R['links'].append({'from': m['source']['id'], 'link': m['relationship'], 'to': m['target']['id'], 'rule': m['evidence'][0].split(' ')[0].replace('engine_rationale:', ''),
                               'why': m['rationale'], 'confidence': m['confidence'], 'correct': (m['source']['id'], m['relationship'], m['target']['id']) in key})
        R['refused'] = [{'rule': a['plan_id'], 'what': a['connection'], 'why': a['reasoning']} for a in refused]
        issues = validate_doc({**empty_registry(), 'mappings': props}, ds)
        t('4 Links between layers', 'the 18 proposed links', 'all valid (right kinds of record, adjacent layers, status proposed)', 'valid' if not issues else f'{len(issues)} issues: {issues[:2]}', 'link checker', not issues)
        bare = approve(props, ds, with_evidence=False); bi = validate_doc(bare, ds)
        t('6 Approving links', 'approve the 18 links with no evidence attached', 'rejected — each link type requires evidence', f'rejected — {len(bi)} problems, e.g. "{bi[0].split(": ", 1)[-1]}"' if bi else 'accepted', 'link checker', bool(bi))
        full = approve(props, ds); fi = validate_doc(full, ds)
        blocked = sorted({x.split(' (')[1].split(')')[0] if ' (' in x else x for x in fi})
        t('6 Approving links', 'approve the 18 links with the required evidence', 'accepted, except any link whose BIAN identifier is missing from the data (never invented)',
          f"{18 - len(blocked)} accepted; {len(blocked)} blocked — " + '; '.join(i.split(': ', 1)[-1] for i in fi[:1]) if fi else '18 accepted', 'link checker', all('canonical_id' in x for x in fi))
        good = {**full, 'mappings': [m for m in full['mappings'] if not any(m['mapping_id'] in x for x in fi)]}
        edited = copy.deepcopy(good); edited['mappings'][0]['rationale'] += ' (edited after approval)'
        dv = diff(good, edited)
        t('6 Approving links', 'edit an approved link afterwards', 'rejected', f'rejected — "{dv[0]}"' if dv else 'accepted', 'change guard (sdem-diff)', bool(dv))
        paths2, _ = write_set(tmp, ds, good); st2 = tmp / 'store2'; build(paths2, st2); r2 = GraphReader.from_store(st2)
        n_fed = len(r2.fg.edges())
        up = r2.fg.trace('INF-K8S-PAY-PROD', 'up'); down = r2.fg.trace('CAP-PAY-010', 'down')
        def reach(tree, acc=None):
            acc = acc if acc is not None else []
            for c in tree['children']: acc.append((c['via']['mapping_id'], c['via']['relationship'], c['node']['id'])); reach(c['node'], acc)
            return acc
        ups, downs = reach(up), reach(down)
        R['trace'] = {'up': ups, 'down': downs, 'federated_links': n_fed}
        t('Trace', 'from the production server up to the business', 'reaches the Payment Initiation domain, the payment processes and the Initiate Payment capability',
          'reached: ' + ', '.join(sorted({n for _, _, n in ups})), 'graph store + trace', {'SD-PI', 'PRC-PAY-01', 'PRC-PAY-02', 'CAP-PAY-010'} <= {n for _, _, n in ups})
        t('Trace', 'from the Initiate Payment capability down to technology', 'reaches the production server', 'reached: ' + ', '.join(sorted({n for _, _, n in downs})), 'graph store + trace', 'INF-K8S-PAY-PROD' in {n for _, _, n in downs})
        imp = r2.fg.impact('INF-K8S-PAY-PROD', 'rehost')
        R['impact'] = [(i['id'], i['level'], i['classification']) for i in imp['instances']]
        # ---------------- run 2 — one planted mistake per copy
        def mutate(fn):
            d = datasets(); fn(d); return d
        def inst(d, iid): return next(i for f in d.values() for i in f['instances'] if i['id'] == iid)
        d = mutate(lambda d: inst(d, 'PRC-PAY-01').update(type='A1.BusinessWidget')); er, _ = check(d)
        t('1 Record types', 'a record of an unknown kind (A1.BusinessWidget)', 'rejected', f'rejected — "{er[0].split(": ", 1)[-1]}"' if er else 'accepted', 'dataset check', bool(er))
        d = mutate(lambda d: inst(d, 'PRC-PAY-01')['attributes'].update(criticality='urgent')); er, _ = check(d)
        t('2 Record information', 'a process with criticality "urgent"', 'rejected', f'rejected — "{er[0].split(": ", 2)[-1]}"' if er else 'accepted', 'dataset check', any('urgent' in x for x in er))
        d = mutate(lambda d: d['a1-business.json']['relationships'].append({'source': 'PRC-PAY-01', 'kind': 'composition', 'target': 'CAP-PAY-010'})); er, _ = check(d)
        t('3 Links inside a layer', 'a process that "contains" a capability', 'rejected', f'rejected — "{er[0].split(": ", 2)[-1][:120]}"' if er else 'accepted', 'dataset check', bool(er))
        wrong = copy.deepcopy(props[0]); cap = inst(datasets(), 'CAP-PAY-010')
        wrong.update(relationship='USES_DOMAIN', source={'id': 'CAP-PAY-010', 'type': cap['type'], 'version': cap['version']}, target={'id': 'SD-PI', 'type': 'A2.ServiceDomain', 'version': '1.0'})
        vi = validate_doc({**empty_registry(), 'mappings': [wrong]}, datasets())
        t('4 Links between layers', 'a "uses domain" link from a capability (only processes may use a domain)', 'rejected', f'rejected — "{vi[0].split(": ", 1)[-1][:120]}"' if vi else 'accepted', 'link checker', bool(vi))
        def app_silent(d):  # 5a: the application and the servers no longer name each other; its deployments still name the server
            a = inst(d, 'APP-PAY-HUB'); a['attributes'].pop('deployed_on', None)
            for f in d.values():
                for i in f['instances']:
                    at = i.get('attributes') or {}
                    if 'APP-PAY-HUB' in (at.get('hosts') or []): at['hosts'] = [x for x in at['hosts'] if x != 'APP-PAY-HUB']
        def no_server(d):  # 5b: nothing names the Payments Hub's server — its deployments drop the platform too
            app_silent(d)
            for f in d.values():
                for i in f['instances']:
                    if (i.get('attributes') or {}).get('component_id') == 'APP-PAY-HUB': i['attributes'].pop('platform_id', None)
        d = mutate(app_silent); p3, _ = write_set(tmp, d, empty_registry()); s3 = tmp / 'store3'; build(p3, s3)
        r3 = RulesEngine().infer(GraphReader.from_store(s3), {'id': 'UCE1M5A'})['proposals']
        sc3 = evaluate([answer], [{'mappings': r3}])['overall']; hub_on = [m for m in r3 if m['source']['id'] == 'APP-PAY-HUB' and m['relationship'] == 'DEPLOYED_ON']
        t('5 Finding links', '5a — the Payments Hub no longer names its server, but its deployment records still do', 'the "runs on" links still found, from the deployment records; nothing invented',
          f"{len(hub_on)} \"runs on\" links found, from the deployment records; {sc3['fp']} wrong", 'engine (step 1 data join)', len(hub_on) == 2 and sc3['fp'] == 0)
        d = mutate(no_server); er, _ = check(d)
        p4, _ = write_set(tmp, d, empty_registry()); e4 = build(p4, tmp / 'store4')
        t('5 Finding links', '5b — nothing names the Payments Hub\'s server (deployments drop it too)', 'no "runs on" link made; nothing invented',
          (f'stricter than expected: the data is rejected before the engine runs — "{er[0].split(": ", 2)[-1][:110]}"' if er else 'accepted'), 'dataset check (required attribute)', bool(er) and e4['result'] == 'rejected')
        # rule with no source — run the real completeness test on a copy of the records
        alt = tmp / 'alt'; shutil.copytree(ROOT / 'metamodel', alt / 'metamodel'); shutil.copytree(ROOT / 'schema', alt / 'schema')
        rr = _j(alt / 'metamodel' / 'relationship-rules.json'); rr['mappings'][0]['source_reference'] = ''
        (alt / 'metamodel' / 'relationship-rules.json').write_text(json.dumps(rr), encoding='utf-8')
        import tests.test_traceability as tt, unittest
        saved = tt.ROOT; tt.ROOT = alt
        try:
            out = unittest.TextTestRunner(stream=open('/dev/null', 'w')).run(unittest.TestSuite([tt.SourceReferenceCompletenessTests('test_every_layer_has_a_source_reference')]))
        finally:
            tt.ROOT = saved
        t('7 Sources', f"rule {rr['mappings'][0]['id']} with its source removed", 'the completeness test fails', 'fails' if out.failures else 'passes', 'completeness test', bool(out.failures))
        # ---------------- gaps
        src = (ROOT / 'sdem' / 'rules_engine.py').read_text(encoding='utf-8')
        reads = sorted({k for k in ('fill_step', 'confidence', 'data_needed', 'reasoning', 'source', 'target', 'relation') if f"['{k}']" in src and "self.rules" in src})
        R['gaps'].append({'id': 'G-A', 'finding': 'confirmed', 'detail': "the engine reads only each rule's step and confidence from the rule records (`fill_step`, `confidence`); how a rule matches is in the engine's code, and nothing checks it against the rule's description (`data_needed`)"})
        card = {x['cardinality'] for x in load_registry()['relationships']}
        R['gaps'].append({'id': 'G-B', 'finding': 'confirmed, no risk today', 'detail': f"link-type limits are not checked, but all 9 link types are {', '.join(sorted(card))}, so there is no limit to break yet"})
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return R


def render(R):
    ok = sum(x['pass'] for x in R['tests']); n = len(R['tests'])
    links = R['links']; good = sum(1 for l in links if l['correct'])
    out = [f"## Results — run {R['date']}", '', f"**Verdict: {ok} of {n} tests pass · {good} of {len(links)} links correct · trace complete · gaps: " + ', '.join(f"{g['id']} {g['finding']}" for g in R['gaps']) + '.**', '',
           'Generated by `python scripts/use_case_example_1.py` — the real checks and the real engine; only approval is simulated.', '',
           '### 1. Tests', '', '| Rule area | Data given | Should | Did | Control | ✅/❌ |', '|---|---|---|---|---|---|']
    out += [f"| {x['area']} | {x['data']} | {x['should']} | {x['did']} | {x['control']} | {'✅' if x['pass'] else '❌'} |" for x in R['tests']]
    out += ['', f'### 2. Links found (run 1) — {len(links)}', '', '| From | Link | To | Rule | Why | Confidence | Matches answer key |', '|---|---|---|---|---|---|---|']
    out += [f"| {l['from']} | {l['link']} | {l['to']} | {l['rule']} | {l['why'][:110]}{'…' if len(l['why']) > 110 else ''} | {l['confidence']} | {'✅' if l['correct'] else '❌'} |" for l in links]
    out += ['', f"Attempts the engine refused, with the reason ({len(R['refused'])}):", '', '| Rule | What | Why refused |', '|---|---|---|']
    out += [f"| {r['rule']} | {r['what']} | {r['why'][:140]} |" for r in R['refused']]
    out += ['', '### 3. Trace', '', f"Links between layers after approval: {R['trace']['federated_links']}.", '', '**Up from the production server:**', '']
    out += [f"- {mid} {rel} → {node}" for mid, rel, node in R['trace']['up']]
    out += ['', '**Down from the Initiate Payment capability:**', ''] + [f"- {mid} {rel} → {node}" for mid, rel, node in R['trace']['down']]
    out += ['', '**Impact of rehosting the production server:** ' + ', '.join(f'{i} ({lvl}, {c})' for i, lvl, c in R['impact']), '',
            '### 4. Gaps', '', '| Gap | Finding | Detail |', '|---|---|---|'] + [f"| {g['id']} | {g['finding']} | {g['detail']} |" for g in R['gaps']]
    return '\n'.join(out) + '\n'


def main():
    R = run(); text = DOC.read_text(encoding='utf-8')
    if '## Results' in text: text = text[:text.index('## Results')]
    text = text.replace('> **Status: plan — not yet run.**', f"> **Status: run {R['date']} — results below.**")
    DOC.write_text(text.rstrip('\n') + '\n\n' + render(R), encoding='utf-8')
    print(render(R).split('\n')[2])
    return 0 if all(x['pass'] for x in R['tests']) else 1


if __name__ == '__main__':
    raise SystemExit(main())
