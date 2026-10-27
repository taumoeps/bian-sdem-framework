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
    mode = {'kind': 'good'}
    def t(area, data, should, did, ctl, ev, ok, kind=None):
        R['tests'].append({'area': area, 'data': data, 'should': should, 'did': did, 'controls': ctl, 'evidence': ev, 'pass': bool(ok), 'kind': kind or mode['kind']})
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
          f'rejected — {len(bi)} problems, e.g. "{bi[0].split(": ", 1)[-1]}"' if bi else 'accepted', 'CTL-06', 'run1-07-approve-without-evidence.json', bool(bi), 'bad')
        full = approve(props); fi = validate_doc(full, ds); E['run1-08-approve-with-evidence.json'] = {'registry': full, 'issues': fi}
        blocked = [m['mapping_id'] for m in full['mappings'] if any(m['mapping_id'] in x for x in fi)]
        t('6 Approving links', 'approve the 18 links with the required evidence', 'accepted, except a link whose BIAN identifier is missing from the data (never invented)',
          (f"{18 - len(blocked)} accepted; {len(blocked)} blocked — " + fi[0].split(': ', 1)[-1]) if fi else '18 accepted', 'CTL-06', 'run1-08-approve-with-evidence.json', all('canonical_id' in x for x in fi))
        # the link that cannot be approved is not deleted (links are never deleted): it stays "proposed" until its BIAN identifier is supplied.
        # Finding F-1: marking it "needs review" instead is refused — "needs review" is held to the approval rule for BIAN identifiers.
        held = [next(p_ for p_ in props if p_['mapping_id'] == b) for b in blocked]
        nr = validate_doc({**empty_registry(), 'mappings': [dict(h, status='needs_review') for h in held]}, ds)
        R['findings'] = [{'id': 'F-1', 'what': 'a link that is waiting for its BIAN identifier cannot be marked "needs review" — that status is held to the approval rule',
                          'control_message': nr[0].split(': ', 1)[-1] if nr else None, 'consequence': 'the link stays "proposed"; owner to decide whether "needs review" should be allowed without the identifier'}] if nr else []
        good = {**full, 'mappings': [m for m in full['mappings'] if m['mapping_id'] not in blocked] + held}; E['run1-09-approved-registry.json'] = good
        ok_tr = diff(E['run1-03-proposals.json'], {**good, 'mappings': [m for m in good['mappings']]}); E['run1-09b-proposed-to-approved.json'] = ok_tr
        t('6 Approving links', 'change 17 proposed links to approved; the blocked one stays proposed (allowed status changes)', 'allowed', 'allowed' if not ok_tr else f'blocked — {ok_tr[0]}', 'CTL-07', 'run1-09b-proposed-to-approved.json', not ok_tr)
        edited = copy.deepcopy(good); edited['mappings'][0]['rationale'] += ' (edited after approval)'; dv = diff(good, edited); E['run1-10-edit-after-approval.json'] = dv
        t('6 Approving links', 'edit an approved link afterwards', 'rejected', f'rejected — "{dv[0]}"' if dv else 'accepted', 'CTL-07', 'run1-10-edit-after-approval.json', bool(dv), 'bad')
        st2 = tmp / 'store2'; build(write_set(tmp, ds, good), st2); r2 = GraphReader.from_store(st2); E['run1-11-load-record.json'] = _j(st2 / 'load-record.json')
        def reach(tree, acc):
            for c in tree['children']: acc.append((c['via']['mapping_id'], c['via']['relationship'], c['node']['id'])); reach(c['node'], acc)
            return acc
        ups, downs = reach(r2.fg.trace('INF-K8S-PAY-PROD', 'up'), []), reach(r2.fg.trace('CAP-PAY-010', 'down'), [])
        imp = r2.fg.impact('INF-K8S-PAY-PROD', 'rehost')
        R['trace'] = {'up': ups, 'down': downs, 'federated_links': len(r2.fg.edges())}; R['impact'] = [(i['id'], i['level'], i['classification']) for i in imp['instances']]
        E['run1-12-trace-and-impact.json'] = {'trace': R['trace'], 'impact': imp}
        t('Trace', 'from the production server up to the business', 'reaches the Payment Initiation domain, the payment processes and the Initiate Payment capability',
          'reached: ' + ', '.join(sorted({n for _, _, n in ups})), 'output (trace)', 'run1-12-trace-and-impact.json', {'SD-PI', 'PRC-PAY-01', 'PRC-PAY-02', 'CAP-PAY-010'} <= {n for _, _, n in ups}, 'output')
        t('Trace', 'from the Initiate Payment capability down to technology', 'reaches the production server', 'reached: ' + ', '.join(sorted({n for _, _, n in downs})),
          'output (trace)', 'run1-12-trace-and-impact.json', 'INF-K8S-PAY-PROD' in {n for _, _, n in downs}, 'output')
        # controls exercised on good data that the steps above do not reach
        from sdem.validate import check_schema
        schemas = {json.loads(p_.read_text())['title']: json.loads(p_.read_text()) for p_ in (ROOT / 'schema' / 'entities').glob('*/*.schema.json')}
        bad_s = [i['id'] for d in ds.values() for i in d['instances'] if check_schema(i, schemas[i['type']])]
        E['run1-13-schemas.json'] = {'records_checked': n_rec, 'failing': bad_s}
        t('2 Record information (format)', f'every one of the {n_rec} records against its per-entity schema', 'all match', f'{n_rec - len(bad_s)} match, {len(bad_s)} fail', 'CTL-04', 'run1-13-schemas.json', not bad_s)
        e2, _ = check(ds, good); E['run1-14-approved-links-resolve.json'] = e2
        t('4 Links between layers (resolution)', 'the 17 approved links against the datasets', 'every end exists', 'all resolve' if not e2 else f'{len(e2)} errors', 'CTL-08', 'run1-14-approved-links-resolve.json', not e2)
        again = RulesEngine().infer(r2, {'id': 'UCE1R'})['proposals']; appr = {(m['source']['id'], m['relationship'], m['target']['id']) for m in good['mappings'] if m['status'] == 'approved'}
        rep_ = [m for m in again if (m['source']['id'], m['relationship'], m['target']['id']) in appr]; nonp = [m for m in again if m['status'] != 'proposed']
        E['run1-15-engine-second-run.json'] = {'proposals': again, 're_proposed_approved': rep_, 'not_proposed_status': nonp}
        t('5 Finding links (engine discipline)', 'run the engine again after the 17 links are approved', 'never re-proposes an approved link; only ever outputs "proposed"',
          f'{len(again)} proposals ({", ".join(m["relationship"] for m in again) or "none"}); {len(rep_)} re-proposed approved links; {len(nonp)} not "proposed"', 'CTL-10', 'run1-15-engine-second-run.json', not rep_ and not nonp)
        import tests.test_traceability as tt0
        with open(tmp / 't0.out', 'w') as fh:
            o0 = unittest.TextTestRunner(stream=fh).run(unittest.TestSuite([tt0.SourceReferenceCompletenessTests('test_every_layer_has_a_source_reference')]))
        E['run1-19-sources-complete.json'] = {'failures': [str(f[1]).splitlines()[-1] for f in o0.failures]}
        t('7 Sources', 'every entity, link row, link type, rule and attribute in the rulebook', 'all name their source', 'all complete' if not o0.failures else 'incomplete', 'CTL-11', 'run1-19-sources-complete.json', not o0.failures)
        import sdem.confidence as conf
        cmis = conf.apply(write=False); E['run1-16-confidence-rule.json'] = cmis
        t('7 Sources (confidence)', 'every confidence rating in the rulebook', 'all follow the single rule', f'{len(cmis)} disagree', 'CTL-12', 'run1-16-confidence-rule.json', not cmis)
        import contextlib, io, sdem.metamodel_spec as msp
        with contextlib.redirect_stdout(io.StringIO()): cur = msp.main(['--check'])
        E['run1-17-documents-current.json'] = {'detail_level_spec_check_exit_code': cur}
        t('Platform (documents)', 'the governing specification against the rulebook', 'matches (not stale)', 'up to date' if cur == 0 else 'stale', 'CTL-13', 'run1-17-documents-current.json', cur == 0)
        import tests.test_metamodel_spec as tms
        hs = hashlib.sha256(tms.HIGH.read_bytes()).hexdigest(); E['run1-18-high-level-spec.json'] = {'sha256': hs, 'pinned': tms.HIGH_SHA256}
        t('Platform (frozen spec)', "the owner's high-level specification", 'unchanged', 'unchanged (checksum matches)' if hs == tms.HIGH_SHA256 else 'changed', 'CTL-14', 'run1-18-high-level-spec.json', hs == tms.HIGH_SHA256)
        # ======== run 2 — one planted mistake per copy
        mode['kind'] = 'bad'
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
        bad_rec = copy.deepcopy(inst(datasets(), 'PRC-PAY-01')); bad_rec['attributes']['criticality'] = 'urgent'
        si = check_schema(bad_rec, schemas['A1.BusinessProcess']); E['run2-8-schema-bad-value.json'] = si
        t('2 Record information (format)', 'the "urgent" process record against its schema', 'fails the schema', f'fails — "{si[0]}"' if si else 'passes', 'CTL-04', 'run2-8-schema-bad-value.json', bool(si))
        dang = copy.deepcopy(good); dang['mappings'][0] = {**dang['mappings'][0], 'mapping_id': 'UCE1-DANGLING', 'target': {**dang['mappings'][0]['target'], 'id': 'INF-DOES-NOT-EXIST'}}
        e8, _ = check(datasets(), dang); E['run2-9-dangling-link.json'] = e8
        t('4 Links between layers (resolution)', 'an approved link to a server that does not exist', 'rejected', f'rejected — "{e8[0].split(": ", 2)[-1][:110]}"' if e8 else 'accepted', 'CTL-08', 'run2-9-dangling-link.json', bool(e8))
        st5 = tmp / 'store5'; build(write_set(tmp, datasets(), good), st5); before = {f.name: f.read_bytes() for f in st5.glob('*.graph.json')}
        e5 = build(write_set(tmp, mutate(lambda d: inst(d, 'PRC-PAY-01')['attributes'].update(criticality='urgent')), good), st5)
        same = before == {f.name: f.read_bytes() for f in st5.glob('*.graph.json')}; lr = _j(st5 / 'load-record.json')
        E['run2-10-failed-load.json'] = {'second_build': e5, 'graph_files_unchanged': same, 'load_record_results': [x['result'] for x in lr['entries']]}
        t('Platform (graph store)', 'load bad data over a good knowledge graph', 'load rejected; the last good graph kept; the rejection logged',
          f"load {e5['result']}; graph files {'unchanged' if same else 'CHANGED'}; load record: {', '.join(x['result'] for x in lr['entries'])}", 'CTL-15', 'run2-10-failed-load.json', e5['result'] == 'rejected' and same)
        attr = copy.deepcopy(next(a for a in _j(ROOT / 'metamodel' / 'entity-attributes.json')['attributes'] if a['source'] == 'SDEM' and a['confidence'] == 'low' and a['status'] == 'active'))
        attr['confidence'] = 'high'; ruled = conf.attribute(attr, conf.validated_rules())[0]; E['run2-11-confidence-overclaim.json'] = {'attribute': f"{attr['entity']}.{attr['name']}", 'recorded': 'high', 'rule_says': ruled}
        t('7 Sources (confidence)', f"attribute {attr['entity']}.{attr['name']} (SDEM-defined) rated high", 'the rule disagrees', f'the rule says {ruled}, not high' if ruled != 'high' else 'agrees', 'CTL-12', 'run2-11-confidence-overclaim.json', ruled != 'high')
        stale = tmp / 'stale-spec.md'; stale.write_text('stale', encoding='utf-8'); keep = msp.OUT; msp.OUT = stale
        try:
            with contextlib.redirect_stdout(io.StringIO()): sc = msp.main(['--check'])
        finally:
            msp.OUT = keep
        E['run2-12-stale-document.json'] = {'check_exit_code': sc}
        t('Platform (documents)', 'a governing specification that no longer matches the rulebook', 'reported stale', 'reported stale' if sc == 1 else 'not reported', 'CTL-13', 'run2-12-stale-document.json', sc == 1)
        edited_spec = tmp / 'high.md'; edited_spec.write_text(tms.HIGH.read_text(encoding='utf-8') + ' ', encoding='utf-8'); keep = tms.HIGH; tms.HIGH = edited_spec
        try:
            with open(tmp / 't2.out', 'w') as fh:
                o2 = unittest.TextTestRunner(stream=fh).run(unittest.TestSuite([tms.HighLevelSpecTests('test_high_level_spec_is_unchanged')]))
        finally:
            tms.HIGH = keep
        E['run2-13-high-level-spec-edited.json'] = {'failures': [str(f[1]).splitlines()[-1] for f in o2.failures]}
        t('Platform (frozen spec)', "the owner's specification with one character added", 'the freeze test fails', 'fails' if o2.failures else 'passes', 'CTL-14', 'run2-13-high-level-spec-edited.json', bool(o2.failures))
        # ======== gaps
        R['gaps'] = [{'id': 'G-A', 'finding': 'confirmed', 'detail': "the engine reads only each rule's step and confidence from the rulebook; how a rule matches is in the engine's code, and nothing checks it against the rule's description"},
                     {'id': 'G-B', 'finding': 'confirmed, no risk today', 'detail': 'link-type limits are not checked, but all 9 link types are ' + ', '.join(sorted({x['cardinality'] for x in load_registry()['relationships']})) + ', so there is no limit to break yet'}]
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return R


def control_summary(R):
    reg = [c for c in _j(ROOT / 'metamodel' / 'controls.json')['controls'] if c.get('status', 'built') == 'built' and c.get('tested_by', 'use-case-example-1') == 'use-case-example-1']; out = []
    for c in reg:
        rows = sorted([x for x in R['tests'] if c['id'] in x['controls']], key=lambda x: x['controls'].index(c['id']))  # a test led by this control first
        g = [x for x in rows if x['kind'] == 'good']; b = [x for x in rows if x['kind'] == 'bad']
        mark = lambda xs: ('✅' if all(x['pass'] for x in xs) else '❌') if xs else '—'
        out.append({'id': c['id'], 'area': c['rule_area'], 'enforces': c['control'], 'good': mark(g), 'bad': mark(b),
                    'output': (b[0]['did'] if b else g[0]['did'] if g else 'not exercised'), 'evidence': sorted({e.strip() for x in rows for e in x['evidence'].split(',')})})
    return out


def write_evidence(R):
    """The evidence pack: every control outcome as a file, with a manifest of SHA-256 checksums, the commit and the date."""
    if EVID.exists(): shutil.rmtree(EVID)
    EVID.mkdir(parents=True)
    files = {}
    for name, obj in R['evidence'].items():
        text = json.dumps(obj, indent=2, ensure_ascii=False, default=str) + '\n'; (EVID / name).write_text(text, encoding='utf-8')
        files[name] = hashlib.sha256(text.encode('utf-8')).hexdigest()
    R['controls'] = control_summary(R)
    res = {'run_date': R['date'], 'tests': [{k: v for k, v in x.items()} for x in R['tests']], 'controls': R['controls']}
    text = json.dumps(res, indent=2, ensure_ascii=False) + '\n'; (EVID / 'results.json').write_text(text, encoding='utf-8'); files['results.json'] = hashlib.sha256(text.encode('utf-8')).hexdigest()
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
           '### Controls output — what each control did', '', 'Every control in the [controls register](controls-register.md), tested with good data (it must accept) and bad data (it must reject).', '',
           '| Control | Enforces | Good data | Bad data | Output (the control\'s own message) | Evidence |', '|---|---|---|---|---|---|']
    out += [f"| {c['id']} | {c['enforces']} | {c['good']} | {c['bad']} | {c['output'][:130]} | {', '.join(f'[{e}](evidence/use-case-example-1/{e})' for e in c['evidence'][:2])}{' …' if len(c['evidence']) > 2 else ''} |" for c in R['controls']]
    out += ['', '### 1. Tests', '', '| # | Rule area | Data given | Should | Did | Control | Evidence | ✅/❌ |', '|---|---|---|---|---|---|---|---|']
    out += [f"| {i} | {x['area']} | {x['data']} | {x['should']} | {x['did']} | {x['controls']} | {ev(x['evidence'])} | {'✅' if x['pass'] else '❌'} |" for i, x in enumerate(R['tests'], 1)]
    out += ['', f"### 2. Links found (run 1) — {len(R['links'])}", '', '| From | Link | To | Rule | Why | Confidence | Matches answer key |', '|---|---|---|---|---|---|---|']
    out += [f"| {l['from']} | {l['link']} | {l['to']} | {l['rule']} | {l['why'][:110]}{'…' if len(l['why']) > 110 else ''} | {l['confidence']} | {'✅' if l['correct'] else '❌'} |" for l in R['links']]
    out += ['', f"Refused by the engine, with the reason ({len(R['refused'])}):", '', '| Rule | What | Why refused |', '|---|---|---|'] + [f"| {r['rule']} | {r['what']} | {r['why'][:140]} |" for r in R['refused']]
    out += ['', '### 3. Trace', '', f"Links between layers after approval: {R['trace']['federated_links']} (one link blocked at approval — test 6).", '', '**Up from the production server:**', '']
    out += [f'- {mid} {rel} → {node}' for mid, rel, node in R['trace']['up']] + ['', '**Down from the Initiate Payment capability:**', ''] + [f'- {mid} {rel} → {node}' for mid, rel, node in R['trace']['down']]
    out += ['', '**Impact of rehosting the production server:** ' + ', '.join(f'{i} ({lvl}, {c})' for i, lvl, c in R['impact']), '',
            '### 4. Gaps', '', '| Gap | Finding | Detail |', '|---|---|---|'] + [f"| {g['id']} | {g['finding']} | {g['detail']} |" for g in R['gaps']]
    if R.get('findings'):
        out += ['', '### 5. Findings for the owner', '', '| ID | What we found | The control\'s message | Consequence |', '|---|---|---|---|'] + [f"| {f['id']} | {f['what']} | {f['control_message']} | {f['consequence']} |" for f in R['findings']]
    return '\n'.join(out) + '\n'


def main():
    R = run(); manifest = write_evidence(R)
    import sdem.controls as sc; sc.main([])  # the register shows each control's latest tested outcome
    text = DOC.read_text(encoding='utf-8')
    if '## Results' in text: text = text[:text.index('## Results')]
    text = text.replace('> **Status: plan — not yet run.**', f"> **Status: run {R['date']} — results below.**")
    DOC.write_text(text.rstrip('\n') + '\n\n' + render(R, manifest), encoding='utf-8')
    print(render(R, manifest).split('\n')[2])
    return 0 if all(x['pass'] for x in R['tests']) else 1


if __name__ == '__main__':
    raise SystemExit(main())
