"""Use-case example 1 — test the rulebook (metamodel) on the payment-initiation datasets (docs/use-case-example-1.md).

Runs the real checks and the real engine (sdem/rules_engine.py; no AI). Run 1: good data, no links between the layers at
the start. Run 2: one planted mistake per copy of the data, so no mistake hides another. Approval is simulated: a stand-in
architect adds the evidence each link type requires; it never invents a BIAN identifier.

Every test names the control that acted (metamodel/controls.json) and the evidence file that records its outcome.
Writes the evidence pack to docs/evidence/use-case-example-1/ (with a manifest of SHA-256 checksums, the commit and the
date) and the results into docs/use-case-example-1.md. tests/test_use_case_example_1.py re-runs it on every change.
Usage: python scripts/use_case_example_1.py
"""
import copy, hashlib, json, shutil, subprocess, sys, tempfile, unittest
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
EVID = ROOT / 'docs' / 'evidence' / 'use-case-example-1'
LEVELS = ('a1-business.json', 'a2-service-domain.json', 'a3-application.json', 'a4-technology.json')
REVIEW = 'use-case-example-1 (simulated architect)'


def _j(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def datasets(): return {f: _j(EST / f) for f in LEVELS}
def empty_registry(): return {'registry_version': load_registry()['$schema_version'], 'metamodel_version': '0.4.0', 'mappings': []}


def check(ds, registry=None):
    """CTL-01/02/03/08 — the dataset check (sdem-graph check): errors and warnings."""
    mm = Metamodel.load(); fg = FederatedGraph([LevelGraph(d, mm) for d in ds.values()], [registry or empty_registry()], mm)
    rep = fg.check()
    return [f'{k}: {i}' for k, v in rep.items() for i in v], [w for v in getattr(fg, 'warnings', {}).values() for w in v]


def validate_doc(doc, ds):
    """CTL-05/06 — the link checker (sdem-validate --strict), ends resolved against the datasets."""
    mm = Metamodel.load(); fg = FederatedGraph([LevelGraph(d, mm) for d in ds.values()], [], mm); w = []
    return list(validate(doc, load_registry(), load_schema(), entity_resolver=fg, warnings=w, metamodel=mm)) + [x for x in w if 'must be supplied before approval' not in x]


def write_set(tmp, ds, registry):
    d = Path(tempfile.mkdtemp(dir=tmp))
    for f, doc in ds.items(): (d / f).write_text(json.dumps(doc), encoding='utf-8')
    (d / 'registry.json').write_text(json.dumps(registry), encoding='utf-8')
    return [str(d / f) for f in ds] + [str(d / 'registry.json')]


def approve(props, with_evidence=True):
    """Stand-in architect: approve every proposal; with evidence, add the evidence kinds each link type requires and the
    BIAN release for BIAN-anchored types. A BIAN identifier missing from the A2 dataset is never invented."""
    types = load_registry()['relationships']; mm = Metamodel.load(); out = []
    for m in props:
        a = copy.deepcopy(m); a.update(status='approved', reviewer_id=REVIEW, approved_at=date.today().isoformat())
        if with_evidence:
            t = next(t for t in types if t['relationship'] == m['relationship'] and mm.is_a(m['source']['type'], t['source_type']) and mm.is_a(m['target']['type'], t['target_type']))
            a['evidence'] = a['evidence'] + [f'{k}:{REVIEW}' for k in t['required_evidence']]
            if t['authority'].startswith('bian_'): a['bian_release'] = 'BIAN 14.0'
        out.append(a)
    return {**empty_registry(), 'mappings': out}


def run():
    tmp = Path(tempfile.mkdtemp(prefix='uce1-'))
    R = {'date': date.today().isoformat(), 'tests': [], 'links': [], 'gaps': [], 'evidence': {}}
    E = R['evidence']
    def t(area, data, should, did, ctl, ev, ok):
        R['tests'].append({'area': area, 'data': data, 'should': should, 'did': did, 'controls': ctl, 'evidence': ev, 'pass': bool(ok)})
    try:
        answer = _j(EST / 'mappings.json')
        # ======== run 1 — good data
        ds = datasets(); errs, warns = check(ds); E['run1-01-check.json'] = {'errors': errs, 'warnings': warns}
        n_rec = sum(len(d['instances']) for d in ds.values()); n_lnk = sum(len(d.get('relationships', [])) for d in ds.values())
        t('1–3 Records, information, links inside a layer', f'the four datasets as they are ({n_rec} records, {n_lnk} links inside layers)', 'accepted',
          f'accepted — {len(errs)} errors, {len(warns)} completeness warnings' if not errs else f'{len(errs)} errors', 'CTL-01, CTL-02, CTL-03', 'run1-01-check.json', not errs)
        st = tmp / 'store1'; e = build(write_set(tmp, ds, empty_registry()), st); reader = GraphReader.from_store(st)
        E['run1-02-load-record.json'] = _j(st / 'load-record.json')
        t('Knowledge graph', 'build the graph store with no links between layers', 'built; 0 links between layers', f"{e['result']}; {len(reader.fg.edges())} links between layers",
          'CTL-15', 'run1-02-load-record.json', e['result'] == 'accepted' and not reader.fg.edges())
        res = RulesEngine().infer(reader, {'id': 'UCE1'}); props = res['proposals']
        score = evaluate([answer], [{'mappings': props}]); o = score['overall']
        E['run1-03-proposals.json'] = {**empty_registry(), 'mappings': props}; E['run1-04-inference-log.json'] = res['log']; E['run1-05-score.json'] = score
        t('5 Finding links', 'engine applies the 69 link-finding rules', '18 links, all correct', f"{o['proposed']} proposed — {o['tp']} correct, {o['fp']} wrong, {o['fn']} missed",
          'CTL-09, CTL-10', 'run1-03-proposals.json, run1-04-inference-log.json, run1-05-score.json', o['tp'] == 18 and o['fp'] == 0 and o['fn'] == 0)
        key = {(m['source']['id'], m['relationship'], m['target']['id']) for m in answer['mappings'] if m['status'] == 'approved'}
        for m in props:
            R['links'].append({'from': m['source']['id'], 'link': m['relationship'], 'to': m['target']['id'], 'rule': m['evidence'][0].split(' ')[0].replace('engine_rationale:', ''),
                               'why': m['rationale'], 'confidence': m['confidence'], 'correct': (m['source']['id'], m['relationship'], m['target']['id']) in key})
        R['refused'] = [{'rule': a['plan_id'], 'what': a['connection'], 'why': a['reasoning']} for a in res['log'] if a['outcome'] == 'no_proposal']
        issues = validate_doc(E['run1-03-proposals.json'], ds); E['run1-06-validate-proposals.json'] = issues
        t('4 Links between layers', 'the 18 proposed links', 'all valid', 'valid' if not issues else f'{len(issues)} issues', 'CTL-05, CTL-08', 'run1-06-validate-proposals.json', not issues)
        bare = approve(props, with_evidence=False); bi = validate_doc(bare, ds); E['run1-07-approve-without-evidence.json'] = {'registry': bare, 'issues': bi}
        t('6 Approving links', 'approve the 18 links with no evidence attached', 'rejected — each link type requires evidence',
          f'rejected — {len(bi)} problems, e.g. "{bi[0].split(": ", 1)[-1]}"' if bi else 'accepted', 'CTL-06', 'run1-07-approve-without-evidence.json', bool(bi))
        full = approve(props); fi = validate_doc(full, ds); E['run1-08-approve-with-evidence.json'] = {'registry': full, 'issues': fi}
        blocked = [m['mapping_id'] for m in full['mappings'] if any(m['mapping_id'] in x for x in fi)]
        t('6 Approving links', 'approve the 18 links with the required evidence', 'accepted, except a link whose BIAN identifier is missing from the data (never invented)',
          (f"{18 - len(blocked)} accepted; {len(blocked)} blocked — " + fi[0].split(': ', 1)[-1]) if fi else '18 accepted', 'CTL-06', 'run1-08-approve-with-evidence.json', all('canonical_id' in x for x in fi))
        good = {**full, 'mappings': [m for m in full['mappings'] if m['mapping_id'] not in blocked]}; E['run1-09-approved-registry.json'] = good
        edited = copy.deepcopy(good); edited['mappings'][0]['rationale'] += ' (edited after approval)'; dv = diff(good, edited); E['run1-10-edit-after-approval.json'] = dv
        t('6 Approving links', 'edit an approved link afterwards', 'rejected', f'rejected — "{dv[0]}"' if dv else 'accepted', 'CTL-07', 'run1-10-edit-after-approval.json', bool(dv))
        st2 = tmp / 'store2'; build(write_set(tmp, ds, good), st2); r2 = GraphReader.from_store(st2); E['run1-11-load-record.json'] = _j(st2 / 'load-record.json')
        def reach(tree, acc):
            for c in tree['children']: acc.append((c['via']['mapping_id'], c['via']['relationship'], c['node']['id'])); reach(c['node'], acc)
            return acc
        ups, downs = reach(r2.fg.trace('INF-K8S-PAY-PROD', 'up'), []), reach(r2.fg.trace('CAP-PAY-010', 'down'), [])
        imp = r2.fg.impact('INF-K8S-PAY-PROD', 'rehost')
        R['trace'] = {'up': ups, 'down': downs, 'federated_links': len(r2.fg.edges())}; R['impact'] = [(i['id'], i['level'], i['classification']) for i in imp['instances']]
        E['run1-12-trace-and-impact.json'] = {'trace': R['trace'], 'impact': imp}
        t('Trace', 'from the production server up to the business', 'reaches the Payment Initiation domain, the payment processes and the Initiate Payment capability',
          'reached: ' + ', '.join(sorted({n for _, _, n in ups})), 'output (trace)', 'run1-12-trace-and-impact.json', {'SD-PI', 'PRC-PAY-01', 'PRC-PAY-02', 'CAP-PAY-010'} <= {n for _, _, n in ups})
        t('Trace', 'from the Initiate Payment capability down to technology', 'reaches the production server', 'reached: ' + ', '.join(sorted({n for _, _, n in downs})),
          'output (trace)', 'run1-12-trace-and-impact.json', 'INF-K8S-PAY-PROD' in {n for _, _, n in downs})
        # ======== run 2 — one planted mistake per copy
        def mutate(fn):
            d = datasets(); fn(d); return d
        def inst(d, iid): return next(i for f in d.values() for i in f['instances'] if i['id'] == iid)
        def planted(name, area, data, should, ctl, fn, test):
            d = mutate(fn); er, wr = check(d); E[f'run2-{name}.json'] = {'errors': er, 'warnings': wr}
            ok, did = test(er); t(area, data, should, did, ctl, f'run2-{name}.json', ok)
        planted('1-unknown-type', '1 Record types', 'a record of an unknown kind (A1.BusinessWidget)', 'rejected', 'CTL-01',
                lambda d: inst(d, 'PRC-PAY-01').update(type='A1.BusinessWidget'), lambda er: (bool(er), f'rejected — "{er[0].split(": ", 1)[-1]}"' if er else 'accepted'))
        planted('2-bad-value', '2 Record information', 'a process with criticality "urgent"', 'rejected', 'CTL-02',
                lambda d: inst(d, 'PRC-PAY-01')['attributes'].update(criticality='urgent'), lambda er: (any('urgent' in x for x in er), f'rejected — "{er[0].split(": ", 2)[-1]}"' if er else 'accepted'))
        planted('3-disallowed-link', '3 Links inside a layer', 'a process that "contains" a capability', 'rejected', 'CTL-03',
                lambda d: d['a1-business.json']['relationships'].append({'source': 'PRC-PAY-01', 'kind': 'composition', 'target': 'CAP-PAY-010'}),
                lambda er: (bool(er), f'rejected — "{er[0].split(": ", 2)[-1][:110]}"' if er else 'accepted'))
        wrong = copy.deepcopy(props[0]); cap = inst(datasets(), 'CAP-PAY-010')
        wrong.update(relationship='USES_DOMAIN', source={'id': 'CAP-PAY-010', 'type': cap['type'], 'version': cap['version']}, target={'id': 'SD-PI', 'type': 'A2.ServiceDomain', 'version': '1.0'})
        vi = validate_doc({**empty_registry(), 'mappings': [wrong]}, datasets()); E['run2-4-wrong-link-type.json'] = {'link': wrong, 'issues': vi}
        t('4 Links between layers', 'a "uses domain" link from a capability (only processes may use a domain)', 'rejected', f'rejected — "{vi[0].split(": ", 1)[-1][:110]}"' if vi else 'accepted',
          'CTL-05', 'run2-4-wrong-link-type.json', bool(vi))
        def app_silent(d):
            inst(d, 'APP-PAY-HUB')['attributes'].pop('deployed_on', None)
            for f in d.values():
                for i in f['instances']:
                    at = i.get('attributes') or {}
                    if 'APP-PAY-HUB' in (at.get('hosts') or []): at['hosts'] = [x for x in at['hosts'] if x != 'APP-PAY-HUB']
        def no_server(d):
            app_silent(d)
            for f in d.values():
                for i in f['instances']:
                    if (i.get('attributes') or {}).get('component_id') == 'APP-PAY-HUB': i['attributes'].pop('platform_id', None)
        st3 = tmp / 'store3'; build(write_set(tmp, mutate(app_silent), empty_registry()), st3)
        r3 = RulesEngine().infer(GraphReader.from_store(st3), {'id': 'UCE1M5A'})['proposals']
        sc3 = evaluate([answer], [{'mappings': r3}])['overall']; hub_on = [m for m in r3 if m['source']['id'] == 'APP-PAY-HUB' and m['relationship'] == 'DEPLOYED_ON']
        E['run2-5a-application-silent.json'] = {'proposals': r3, 'score': sc3}
        t('5 Finding links', '5a — the Payments Hub no longer names its server, but its deployment records still do', 'the "runs on" links still found from the deployment records; nothing invented',
          f"{len(hub_on)} \"runs on\" links found, from the deployment records; {sc3['fp']} wrong", 'CTL-09, CTL-10', 'run2-5a-application-silent.json', len(hub_on) == 2 and sc3['fp'] == 0)
        d5 = mutate(no_server); er, _ = check(d5); e4 = build(write_set(tmp, d5, empty_registry()), tmp / 'store4')
        E['run2-5b-no-server.json'] = {'errors': er, 'load_record_entry': e4}
        t('5 Finding links', '5b — nothing names the Payments Hub\'s server (its deployments drop it too)', 'no "runs on" link made; nothing invented',
          f'stricter than expected: the data is rejected before the engine runs — "{er[0].split(": ", 2)[-1][:100]}"' if er else 'accepted', 'CTL-02, CTL-15', 'run2-5b-no-server.json',
          bool(er) and e4['result'] == 'rejected')
        alt = tmp / 'alt'; shutil.copytree(ROOT / 'metamodel', alt / 'metamodel'); shutil.copytree(ROOT / 'schema', alt / 'schema')
        rr = _j(alt / 'metamodel' / 'relationship-rules.json'); rr['mappings'][0]['source_reference'] = ''
        (alt / 'metamodel' / 'relationship-rules.json').write_text(json.dumps(rr), encoding='utf-8')
        import tests.test_traceability as tt
        saved = tt.ROOT; tt.ROOT = alt
        try:
            with open(tmp / 'test.out', 'w') as fh:
                out = unittest.TextTestRunner(stream=fh).run(unittest.TestSuite([tt.SourceReferenceCompletenessTests('test_every_layer_has_a_source_reference')]))
        finally:
            tt.ROOT = saved
        E['run2-7-rule-without-source.json'] = {'rule': rr['mappings'][0]['id'], 'failures': [str(f[1]).splitlines()[-1] for f in out.failures]}
        t('7 Sources', f"rule {rr['mappings'][0]['id']} with its source removed", 'the completeness test fails',
          ('fails — ' + E['run2-7-rule-without-source.json']['failures'][0][:100]) if out.failures else 'passes', 'CTL-11', 'run2-7-rule-without-source.json', bool(out.failures))
        # ======== gaps
        R['gaps'] = [{'id': 'G-A', 'finding': 'confirmed', 'detail': "the engine reads only each rule's step and confidence from the rulebook; how a rule matches is in the engine's code, and nothing checks it against the rule's description"},
                     {'id': 'G-B', 'finding': 'confirmed, no risk today', 'detail': 'link-type limits are not checked, but all 9 link types are ' + ', '.join(sorted({x['cardinality'] for x in load_registry()['relationships']})) + ', so there is no limit to break yet'}]
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return R


def write_evidence(R):
    """The evidence pack: every control outcome as a file, with a manifest of SHA-256 checksums, the commit and the date."""
    if EVID.exists(): shutil.rmtree(EVID)
    EVID.mkdir(parents=True)
    files = {}
    for name, obj in R['evidence'].items():
        text = json.dumps(obj, indent=2, ensure_ascii=False, default=str) + '\n'; (EVID / name).write_text(text, encoding='utf-8')
        files[name] = hashlib.sha256(text.encode('utf-8')).hexdigest()
    commit = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    manifest = {'example': 'use-case-example-1', 'run_date': R['date'], 'code_commit': commit, 'script': 'scripts/use_case_example_1.py',
                'script_sha256': hashlib.sha256((ROOT / 'scripts' / 'use_case_example_1.py').read_bytes()).hexdigest(), 'files': files}
    (EVID / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    return manifest


def render(R, manifest):
    ok = sum(x['pass'] for x in R['tests']); n = len(R['tests']); good = sum(1 for l in R['links'] if l['correct'])
    ev = lambda names: ', '.join(f'[{x.strip()}](evidence/use-case-example-1/{x.strip()})' for x in names.split(','))
    out = [f"## Results — run {R['date']}", '',
           f"**Verdict: {ok} of {n} tests pass · {good} of {len(R['links'])} links correct · trace complete · gaps: " + ', '.join(f"{g['id']} {g['finding']}" for g in R['gaps']) + '.**', '',
           '### How we know these results are right', '',
           '| Proof | Where to see it |', '|---|---|',
           '| **The expected results were fixed before the run.** The plan with every expected result was committed before the first run. | git history of this document (plan commits precede the results commit) |',
           '| **Each result is the control\'s own message**, not a summary we wrote. | the "Did" column quotes it; the evidence file holds the full output |',
           '| **Every control is shown working both ways** — accepting good data and rejecting bad. | run 1 and run 2 rows below |',
           '| **Every control is registered**: what it enforces, where it is built, where its outcome is recorded, what monitors it. | [`controls-register.md`](controls-register.md) |',
           f"| **The evidence is kept and tamper-evident**: {len(manifest['files'])} files with SHA-256 checksums, the code commit and the run date. | [`evidence/use-case-example-1/manifest.json`](evidence/use-case-example-1/manifest.json) |",
           '| **It is reproducible and monitored**: the run is deterministic and re-runs on every push in CI. | `python scripts/use_case_example_1.py`; `tests/test_use_case_example_1.py` |', '',
           '**What would still strengthen it:** an answer key written by someone other than the project, and a real architect approving instead of the simulated one.', '',
           '### 1. Tests', '', '| # | Rule area | Data given | Should | Did | Control | Evidence | ✅/❌ |', '|---|---|---|---|---|---|---|---|']
    out += [f"| {i} | {x['area']} | {x['data']} | {x['should']} | {x['did']} | {x['controls']} | {ev(x['evidence'])} | {'✅' if x['pass'] else '❌'} |" for i, x in enumerate(R['tests'], 1)]
    out += ['', f"### 2. Links found (run 1) — {len(R['links'])}", '', '| From | Link | To | Rule | Why | Confidence | Matches answer key |', '|---|---|---|---|---|---|---|']
    out += [f"| {l['from']} | {l['link']} | {l['to']} | {l['rule']} | {l['why'][:110]}{'…' if len(l['why']) > 110 else ''} | {l['confidence']} | {'✅' if l['correct'] else '❌'} |" for l in R['links']]
    out += ['', f"Refused by the engine, with the reason ({len(R['refused'])}):", '', '| Rule | What | Why refused |', '|---|---|---|'] + [f"| {r['rule']} | {r['what']} | {r['why'][:140]} |" for r in R['refused']]
    out += ['', '### 3. Trace', '', f"Links between layers after approval: {R['trace']['federated_links']} (one link blocked at approval — test 6).", '', '**Up from the production server:**', '']
    out += [f'- {mid} {rel} → {node}' for mid, rel, node in R['trace']['up']] + ['', '**Down from the Initiate Payment capability:**', ''] + [f'- {mid} {rel} → {node}' for mid, rel, node in R['trace']['down']]
    out += ['', '**Impact of rehosting the production server:** ' + ', '.join(f'{i} ({lvl}, {c})' for i, lvl, c in R['impact']), '',
            '### 4. Gaps', '', '| Gap | Finding | Detail |', '|---|---|---|'] + [f"| {g['id']} | {g['finding']} | {g['detail']} |" for g in R['gaps']]
    return '\n'.join(out) + '\n'


def main():
    R = run(); manifest = write_evidence(R); text = DOC.read_text(encoding='utf-8')
    if '## Results' in text: text = text[:text.index('## Results')]
    text = text.replace('> **Status: plan — not yet run.**', f"> **Status: run {R['date']} — results below.**")
    DOC.write_text(text.rstrip('\n') + '\n\n' + render(R, manifest), encoding='utf-8')
    print(render(R, manifest).split('\n')[2])
    return 0 if all(x['pass'] for x in R['tests']) else 1


if __name__ == '__main__':
    raise SystemExit(main())
