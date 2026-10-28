"""Use-case example 3 — the agent platform carries a change across the architectures (docs/evidence/use-case-example-3.md).

Runs the commands the agent files in .github/agents/ instruct — A4 agent, orchestrator, A3 agent, rules engine, architect —
on a copy of the payment-initiation estate, and the controls with good and bad data. Pass criteria: spec AT-AG-01…08,
sealed in commit 5cbb0ed. Copilot itself is not run here (that is the spike, docs/sdem-agent-platform-spike.md).
Writes the evidence pack to docs/evidence/use-case-example-3/ and the results into docs/evidence/use-case-example-3.md.
Usage: python scripts/use_case_example_3.py
"""
import contextlib, copy, hashlib, io, json, shutil, subprocess, sys, tempfile
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from sdem import agents, cli  # noqa: E402

DOC = ROOT / 'docs' / 'evidence' / 'use-case-example-3.md'
EVID = ROOT / 'docs' / 'evidence' / 'use-case-example-3'
SRC = ROOT / 'examples' / 'payment-initiation'
T = '2026-10-28T00:00:00+00:00'                 # fixed, so the evidence is reproducible
PERSON = 'jane.architect'
A4, A3, ORCH = 'sdem-a4-technology', 'sdem-a3-application', 'sdem-orchestrator'


def sdem(*argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try: code = cli.main([str(a) for a in argv])
        except SystemExit as e: code = e.code
    return code, out.getvalue(), err.getvalue()


def _j(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def _w(p, o): Path(p).parent.mkdir(parents=True, exist_ok=True); Path(p).write_text(json.dumps(o, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')


def change_sets(est):
    """The two change sets the A4 and A3 agents write (their content is the agents' design work)."""
    a4 = {i['id']: i for i in _j(est / 'a4-technology.json')['instances']}
    a3 = {i['id']: i for i in _j(est / 'a3-application.json')['instances']}
    old = copy.deepcopy(a4['INF-K8S-PAY-PROD']); old['lifecycle_status'] = 'deprecated'; old['attributes']['hosts'] = []
    deps = []
    for d in ('DEP-PAYHUB-PROD', 'DEP-PAYEXEC-PROD'):
        x = copy.deepcopy(a4[d]); x['attributes']['platform_id'] = 'INF-K8S-PAY-PROD2'; deps.append({'op': 'update', 'record': x})
    cs4 = {'layer': 'A4', 'reason': 'Rehost production payments from INF-K8S-PAY-PROD onto the new managed cluster INF-K8S-PAY-PROD2',
           'changes': [{'op': 'add', 'record': {'id': 'INF-K8S-PAY-PROD2', 'type': 'A4.SystemSoftware', 'version': '1.31', 'name': 'Managed Kubernetes — payments (production, new cluster)',
                                                 'lifecycle_status': 'active', 'attributes': {'hosts': ['APP-PAY-HUB', 'CMP-PAY-EXEC'], 'product_version': '1.31', 'license': 'Apache-2.0', 'end_of_support': '2028-06-30'}}},
                       {'op': 'update', 'kind': 'rehost', 'record': old}] + deps,
           'relationships': {'add': [{'source': 'INF-K8S-PAY-PROD2', 'kind': 'association', 'target': 'NET-PAY-PRIVATE'}]}}
    hub = copy.deepcopy(a3['APP-PAY-HUB']); hub['attributes']['deployed_on'] = ['INF-K8S-PAY-PROD2', 'INF-K8S-PAY-UAT']
    ex = copy.deepcopy(a3['CMP-PAY-EXEC']); ex['attributes']['deployed_on'] = ['INF-K8S-PAY-PROD2']
    cs3 = {'layer': 'A3', 'reason': 'Re-point the Payments Hub and the Execution Gateway to the new production cluster', 'changes': [{'op': 'update', 'record': hub}, {'op': 'update', 'record': ex}]}
    return cs4, cs3


def run():
    agents._now = lambda: T
    tmp = Path(tempfile.mkdtemp(prefix='uce3-')); R = {'date': date.today().isoformat(), 'criteria': [], 'controls_tests': [], 'steps': []}
    E = {}
    def step(who, cmd, code, out, err): R['steps'].append({'who': who, 'command': ' '.join(str(c) for c in cmd).replace(str(tmp), '<work>'), 'exit': code, 'output': (out + err).replace(str(tmp), '<work>').strip()[:1500]})
    def crit(i, test, ok, did, evidence): R['criteria'].append({'id': i, 'test': test, 'pass': bool(ok), 'did': did, 'evidence': evidence})
    def ctl(control, kind, test, code, out, should_reject, mark):
        rejected = code != 0 and mark in out
        R['controls_tests'].append({'control': control, 'data': kind, 'test': test, 'should': 'rejected' if should_reject else 'accepted',
                                    'did': 'rejected' if code != 0 else 'accepted', 'message': (out.strip().splitlines() or ['—'])[-1 if should_reject else 0][:200].replace(str(tmp), '<work>'),
                                    'pass': (rejected if should_reject else code == 0)})
    try:
        est = tmp / 'est'; shutil.copytree(SRC, est, ignore=shutil.ignore_patterns('graph'))
        drafts = est / 'coordination' / 'drafts'; cs4, cs3 = change_sets(est)
        _w(drafts / 'cs-a4-rehost.json', cs4); _w(drafts / 'cs-a3-repoint.json', cs3)
        # the independent answer for AT-AG-01: sdem impact on the estate before any change
        sdem('build', *sorted(map(str, est.glob('a*.json'))), est / 'mappings.json', '--out', tmp / 'graph-before')
        code, out, err = sdem('impact', 'INF-K8S-PAY-PROD', '--change', 'rehost', '--graph', tmp / 'graph-before', '--json')
        ref = json.loads(out); E['reference-impact-rehost.json'] = ref

        # ---- bad data first, so it is proven that nothing lands (controls)
        args = ('--estate', est)
        code, out, err = sdem('change', 'propose', drafts / 'cs-a4-rehost.json', *args, '--agent', A3, '--person', PERSON)
        ctl('CTL-19', 'bad', 'the A3 agent proposes an A4 change set', code, err, True, 'CTL-19'); step(A3, ['sdem change propose cs-a4-rehost.json --agent', A3], code, out, err)
        bad = copy.deepcopy(cs4); bad['changes'].append({'op': 'update', 'record': copy.deepcopy(cs3['changes'][0]['record'])}); _w(drafts / 'bad-mixed.json', bad)
        code, out, err = sdem('change', 'propose', drafts / 'bad-mixed.json', *args, '--agent', A4, '--person', PERSON)
        ctl('CTL-19', 'bad', 'an A4 change set that also changes an A3 record', code, err, True, 'CTL-19')
        bad = copy.deepcopy(cs4); bad['relationships']['add'].append({'source': 'INF-K8S-PAY-PROD2', 'kind': 'association', 'target': 'APP-PAY-HUB'}); _w(drafts / 'bad-crosslink.json', bad)
        code, out, err = sdem('change', 'propose', drafts / 'bad-crosslink.json', *args, '--agent', A4, '--person', PERSON)
        ctl('CTL-19', 'bad', 'an A4 change set adds a link to an A3 record (a cross-layer link)', code, err, True, 'CTL-19')
        bad = copy.deepcopy(cs4); bad['mappings'] = [{'mapping_id': 'X'}]; _w(drafts / 'bad-registry.json', bad)
        code, out, err = sdem('change', 'propose', drafts / 'bad-registry.json', *args, '--agent', A4, '--person', PERSON)
        ctl('CTL-19', 'bad', 'a change set that tries to write the registry', code, err, True, "unknown property 'mappings'")
        code, out, err = sdem('change', 'propose', drafts / 'cs-a4-rehost.json', *args, '--agent', ORCH, '--person', PERSON)
        ctl('CTL-19', 'bad', 'the orchestrator proposes a change set', code, err, True, 'CTL-19')
        code, out, err = sdem('change', 'propose', drafts / 'cs-a4-rehost.json', *args, '--agent', A4, '--person', '')
        ctl('CTL-20', 'bad', 'a change set without the person behind it', code, err, True, 'CTL-20')
        code, out, err = sdem('change', 'propose', drafts / 'cs-a4-rehost.json', *args, '--agent', '', '--person', PERSON)
        ctl('CTL-20', 'bad', 'a change set without the agent', code, err, True, 'CTL-20')
        bad = {'layer': 'A2', 'reason': 'add a domain', 'changes': [{'op': 'add', 'record': {'id': 'SD-NEW', 'type': 'A2.ServiceDomain', 'version': '1.0', 'name': 'Invented'}}]}; _w(drafts / 'bad-a2.json', bad)
        code, out, err = sdem('change', 'propose', drafts / 'bad-a2.json', *args, '--agent', 'sdem-a2-bian', '--person', PERSON)
        ctl('CTL-19', 'bad', 'the A2 agent adds a service domain without the BIAN catalogue', code, err, True, 'CTL-19')
        bad = copy.deepcopy(cs4); bad['changes'][0]['record']['id'] = 'PRJ-APP-X'; bad['changes'][0]['record']['type'] = 'A4.SystemSoftware'; _w(drafts / 'bad-projected.json', bad)
        code, out, err = sdem('change', 'propose', drafts / 'bad-projected.json', *args, '--agent', A4, '--person', PERSON)
        ctl('CTL-16', 'bad', 'a change set brings a projected (PRJ-) record into real data', code, err, True, 'CTL-16')
        nothing_landed = not agents.Estate(est).events() and _j(est / 'a4-technology.json') == _j(SRC / 'a4-technology.json')

        # ---- round 1: the A4 agent (AT-AG-01)
        code, out, err = sdem('change', 'propose', drafts / 'cs-a4-rehost.json', *args, '--agent', A4, '--person', PERSON)
        step(A4, ['sdem change propose coordination/drafts/cs-a4-rehost.json --estate <est> --agent', A4, '--person', PERSON], code, out, err)
        ctl('CTL-19', 'good', 'the A4 agent proposes its own A4 change set', code, out, False, '')
        ctl('CTL-20', 'good', 'a change set with agent and person', code, out, False, '')
        ev1 = agents.Estate(est).events()[0]
        want = {r['id']: r['classification'] for r in ref['instances']}
        got = {r['id']: r['classification'] for r in ev1['impact']['records']}
        same = all(got.get(k) == v for k, v in want.items()) and set(ref['mappings_to_supersede']) <= set(ev1['impact']['mappings_to_supersede'])
        a12 = {r['id']: r['classification'] for r in ev1['impact']['records'] if r['level'] in ('A1', 'A2')}
        crit('AT-AG-01', 'A4 agent drafts the rehost of INF-K8S-PAY-PROD', code == 0 and same and got.get('APP-PAY-HUB') == got.get('CMP-PAY-EXEC') == 'design_change_required'
             and ev1['impact']['mappings_to_supersede'] == ['PAY-108', 'PAY-111'] and set(a12.values()) == {'no_impact'},
             f"CS-001 accepted; CE-001 stored with impact. APP-PAY-HUB and CMP-PAY-EXEC: design change required; supersede {', '.join(ev1['impact']['mappings_to_supersede'])}; "
             f"A1/A2 ({', '.join(sorted(a12))}): no impact. Matches `sdem impact INF-K8S-PAY-PROD --change rehost` on the estate before the change for every record it lists.",
             'events/CE-001.json, change-sets/CS-001.json, reference-impact-rehost.json')

        # ---- the orchestrator plans (AT-AG-02)
        code, out, err = sdem('work', 'plan', '--event', 'CE-001', *args, '--agent', ORCH, '--person', PERSON)
        step(ORCH, ['sdem work plan --event CE-001 --estate <est> --agent', ORCH, '--person', PERSON], code, out, err)
        work = agents.Estate(est).work()
        layers = sorted({w['layer'] for w in work})
        crit('AT-AG-02', 'Orchestrator plans the work', code == 0 and work and set(layers) <= {'A3', 'A4'},
             f"{len(work)} work items, layers {layers}: " + '; '.join(f"{w['id']} {w['records'][0]}" for w in work) + '. None for A1 or A2. (A4 needed none: the A4 agent changed its own deployments in CS-001.)',
             'work-items/')

        # ---- claim by the wrong agent (CTL-19), then round 2: the A3 agent (AT-AG-03)
        code, out, err = sdem('work', 'claim', 'WI-001', *args, '--agent', A4, '--person', PERSON)
        ctl('CTL-19', 'bad', 'the A4 agent claims an A3 work item', code, err, True, 'CTL-19')
        code, out, err = sdem('work', 'claim', 'WI-001', *args, '--agent', A3, '--person', '')
        ctl('CTL-20', 'bad', 'a work item claimed without the person', code, err, True, 'CTL-20')
        for w in work:
            code, out, err = sdem('work', 'claim', w['id'], *args, '--agent', A3, '--person', PERSON); step(A3, ['sdem work claim', w['id'], '--agent', A3, '--person', PERSON], code, out, err)
        code, out, err = sdem('change', 'propose', drafts / 'cs-a3-repoint.json', *args, '--agent', A3, '--person', PERSON, '--work', *[w['id'] for w in work])
        step(A3, ['sdem change propose coordination/drafts/cs-a3-repoint.json --estate <est> --agent', A3, '--person', PERSON, '--work', *[w['id'] for w in work]], code, out, err)
        cs2 = _j(est / 'coordination' / 'change-sets' / 'CS-002.json')
        only_a3 = all(c['record']['type'].startswith('A3.') for c in cs2['changes'])
        code2, out2, err2 = sdem('work', 'plan', '--event', 'CE-002', *args, '--agent', ORCH, '--person', PERSON)
        step(ORCH, ['sdem work plan --event CE-002 --estate <est> --agent', ORCH, '--person', PERSON], code2, out2, err2)
        codel, outl, errl = sdem('link', *sorted(map(str, est.glob('a*.json'))), est / 'mappings.json', '--out', tmp / 'links')
        step('rules engine', ['sdem link <est>/a*.json <est>/mappings.json --out <links>'], codel, outl, errl)
        props = _j(tmp / 'links' / 'proposals.json')['mappings']; E['proposals.json'] = _j(tmp / 'links' / 'proposals.json')
        new_links = sorted(f"{m['source']['id']} {m['relationship']} {m['target']['id']}" for m in props)
        want_links = ['APP-PAY-HUB DEPLOYED_ON INF-K8S-PAY-PROD2', 'CMP-PAY-EXEC DEPLOYED_ON INF-K8S-PAY-PROD2']
        crit('AT-AG-03', 'A3 agent answers its work items', code == 0 and only_a3 and all(l in new_links for l in want_links),
             f"CS-002 accepted, A3 records only, answering {', '.join(cs2['work_items'])}; CE-002 planned: {out2.splitlines()[0] if out2 else '—'}. "
             f"The rules engine proposes: {'; '.join(new_links)} (rule S33, confidence {', '.join(sorted({str(m['confidence']) for m in props}))}).",
             'change-sets/CS-002.json, events/, proposals.json')

        # ---- AG-S08: a direct edit of a dataset (bypassing change sets) is caught; a person can adopt it
        a4p = est / 'a4-technology.json'; keep = a4p.read_bytes(); d = _j(a4p)
        for i in d['instances']:
            if i['id'] == 'INF-K8S-PAY-PROD2': i['name'] = 'Managed Kubernetes — payments (production, region B)'
        a4p.write_text(json.dumps(d, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
        code, out, err = sdem('check', '--estate', est)
        ctl('CTL-20', 'bad', 'a dataset edited directly, outside a change set (AG-S08)', 1 if 'AG-S08' in out else 0, out, True, 'AG-S08')
        code, out, err = sdem('change', 'adopt', '--estate', est, '--layer', 'A4', '--person', A4, '--reason', 'x')
        ctl('CTL-20', 'bad', 'an agent adopts a direct edit as if it were a person', code, err, True, 'CTL-20')
        a4p.write_bytes(keep)                                     # undo the edit: the example's data stays as the agents left it
        code, out, err = sdem('check', '--estate', est)
        ctl('CTL-20', 'good', 'datasets exactly as the recorded change sets left them', 0 if code == 0 and 'AG-S08' not in out else 1, out, False, '')

        # ---- AT-AG-04/05/06 from the control tests
        t = R['controls_tests']
        def found(test): return next(x for x in t if x['test'] == test)['pass']
        crit('AT-AG-04', 'An agent tries to change another layer', found('the A3 agent proposes an A4 change set') and found('an A4 change set that also changes an A3 record') and found('the A4 agent claims an A3 work item'),
             'rejected by CTL-19 three ways: the A3 agent proposing an A4 change set; an A4 change set touching an A3 record; the A4 agent claiming an A3 work item', 'controls table')
        code, out, err = sdem('work', 'plan', '--help')
        approve_cmd = any(w in out for w in ('approve', 'approved'))
        reg = _j(est / 'mappings.json'); unapproved = copy.deepcopy(reg)
        p0 = copy.deepcopy(props[0]); p0.update(mapping_id='PAY-299', status='approved'); unapproved['mappings'].append(p0); _w(tmp / 'bad-approval.json', unapproved)
        codev, outv, errv = sdem('validate', '--strict', tmp / 'bad-approval.json')
        ctl('governance', 'bad', 'a link marked approved without reviewer, time or evidence', codev, outv + errv, True, 'requires reviewer_id')
        crit('AT-AG-05', 'An agent tries to add a cross-layer link or approve', found('an A4 change set adds a link to an A3 record (a cross-layer link)') and found('a change set that tries to write the registry')
             and not approve_cmd and codev != 0,
             'a cross-layer link and a registry write in a change set are rejected (CTL-19, change-set format); no agent command can approve; a link set to approved without a reviewer is rejected by the governance check (`sdem validate`)',
             'controls table')
        crit('AT-AG-06', 'A change set without agent or person', found('a change set without the person behind it') and found('a change set without the agent') and found('a work item claimed without the person'),
             'rejected by CTL-20: no person; no agent; a work item claimed without a person', 'controls table')

        # ---- AT-AG-07: the round limit, on a second copy of the estate
        est2 = tmp / 'est2'; shutil.copytree(SRC, est2, ignore=shutil.ignore_patterns('graph')); _w(est2 / 'coordination' / 'drafts' / 'cs.json', cs4)
        sdem('change', 'propose', est2 / 'coordination' / 'drafts' / 'cs.json', '--estate', est2, '--agent', A4, '--person', PERSON)
        code, out, err = sdem('work', 'plan', '--event', 'CE-001', '--estate', est2, '--agent', ORCH, '--person', PERSON, '--max-rounds', '1')
        step(ORCH, ['sdem work plan --event CE-001 --max-rounds 1  (round limit test)'], code, out, err)
        crit('AT-AG-07', 'A ripple that keeps producing impact', code == 1 and 'STOP' in out, out.strip() or err.strip(), 'steps')

        # ---- AT-AG-08: the architect approves (sdem approve), supersedes and merges; the graph rebuilds
        chosen = sorted((m for m in props if m['relationship'] == 'DEPLOYED_ON' and m['target']['id'] == 'INF-K8S-PAY-PROD2'), key=lambda x: x['source']['id'])
        code, out, err = sdem('approve', chosen[0]['mapping_id'], '--proposals', tmp / 'links' / 'proposals.json', '--estate', est, '--reviewer', A3, '--evidence', 'deployment_design:PAY-REHOST-2026-10#cutover', '--supersedes', 'PAY-108')
        ctl('CTL-21', 'bad', 'an agent approves a link (reviewer = an agent name)', code, err, True, 'CTL-21')
        for n, (m, old) in enumerate(zip(chosen, ('PAY-108', 'PAY-111')), 1):
            code, out, err = sdem('approve', m['mapping_id'], '--proposals', tmp / 'links' / 'proposals.json', '--estate', est, '--reviewer', PERSON,
                                  '--evidence', 'deployment_design:PAY-REHOST-2026-10#cutover', '--supersedes', old, '--id', f'PAY-2{n:02d}', '--date', '2026-10-28')
            step('architect', ['sdem approve', m['mapping_id'], '--proposals <links>/proposals.json --estate <est> --reviewer', PERSON, '--evidence deployment_design:PAY-REHOST-2026-10#cutover --supersedes', old, '--id', f'PAY-2{n:02d}'], code, out, err)
            if n == 1: ctl('CTL-21', 'good', 'a person approves a link with the required evidence', code, out, False, '')
        reg = _j(est / 'mappings.json'); E['registry-after-approval.json'] = reg
        cv, ov, ev_ = sdem('validate', '--strict', est / 'mappings.json'); step('architect', ['sdem validate --strict <est>/mappings.json'], cv, ov, ev_)
        cc, oc, ec = sdem('check', *sorted(map(str, est.glob('a*.json'))), est / 'mappings.json'); step('architect', ['sdem check <est>/a*.json <est>/mappings.json'], cc, oc.splitlines()[-1] if oc else '', ec)
        cb, ob, eb = sdem('build', *sorted(map(str, est.glob('a*.json'))), est / 'mappings.json', '--out', tmp / 'graph'); step('architect', ['sdem build … --out <graph>'], cb, ob.splitlines()[-1] if ob else '', eb)
        ct, ot, et = sdem('trace', 'APP-PAY-HUB', '--direction', 'down', '--graph', tmp / 'graph'); step('architect', ['sdem trace APP-PAY-HUB --direction down --graph <graph>'], ct, ot, '')
        E['trace-after.txt'] = ot
        evs = agents.Estate(est).events(); wis = agents.Estate(est).work()
        sets = [_j(f) for f in sorted((est / 'coordination' / 'change-sets').glob('CS-*.json'))]
        traceable = all(x['agent'] and x['person'] for x in evs + sets) and all(h['agent'] and h['person'] for w in wis for h in w['history']) and all(w['history'][-1]['status'] == 'done' for w in wis)
        crit('AT-AG-08', 'The architect reviews and merges', cv == 0 and cc == 0 and cb == 0 and 'INF-K8S-PAY-PROD2' in ot and 'PAY-201' in ot and 'PAY-108' not in ot and traceable and nothing_landed,
             f"the architect approved PAY-201, PAY-202 with `sdem approve` (superseding PAY-108, PAY-111, deployment evidence); validate, check and build pass; the trace shows APP-PAY-HUB → INF-K8S-PAY-PROD2 via PAY-201 and no longer PAY-108. "
             f"On record: {len(sets)} change sets, {len(evs)} change events, {len(wis)} work items (all done) — every one with agent and person. The rejected attempts left no trace in the data.",
             'events/, work-items/, change-sets/, registry-after-approval.json, trace-after.txt')
        for e_ in evs: E[f"events/{e_['id']}.json"] = e_
        for w_ in wis: E[f"work-items/{w_['id']}.json"] = w_
        for s in sets: E[f"change-sets/{s['id']}.json"] = s
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    R['evidence'] = E
    mark = lambda xs: ('✅' if all(x['pass'] for x in xs) else '❌') if xs else '—'
    R['controls'] = [{'id': c, 'good': mark([x for x in R['controls_tests'] if x['control'] == c and x['data'] == 'good']),
                      'bad': mark([x for x in R['controls_tests'] if x['control'] == c and x['data'] == 'bad'])} for c in ('CTL-19', 'CTL-20', 'CTL-21')]
    return R


def write_evidence(R):
    if EVID.exists(): shutil.rmtree(EVID)
    EVID.mkdir(parents=True); files = {}
    for name, obj in list(R['evidence'].items()) + [('results.json', {k: v for k, v in R.items() if k != 'evidence'})]:
        text = obj if isinstance(obj, str) else json.dumps(obj, indent=2, ensure_ascii=False) + '\n'
        p = EVID / name; p.parent.mkdir(parents=True, exist_ok=True); p.write_text(text, encoding='utf-8'); files[name] = hashlib.sha256(text.encode('utf-8')).hexdigest()
    m = {'example': 'use-case-example-3', 'run_date': R['date'], 'code_commit': subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=ROOT, capture_output=True, text=True).stdout.strip(), 'files': files}
    (EVID / 'manifest.json').write_text(json.dumps(m, indent=2) + '\n', encoding='utf-8')


def render(R):
    cell = lambda x: str(x).replace('|', '/').replace('\n', ' ')
    n = sum(c['pass'] for c in R['criteria']); k = sum(c['pass'] for c in R['controls_tests'])
    out = [f"## Results — run {R['date']}", '',
           f"**Verdict:** {n} of {len(R['criteria'])} sealed criteria met; controls {k} of {len(R['controls_tests'])} tests pass (good data accepted, bad data rejected).", '',
           'Generated by `python scripts/use_case_example_3.py`; evidence in [`evidence/use-case-example-3/`](evidence/use-case-example-3/manifest.json). '
           'What Copilot itself does with the agent files is checked by the spike in your VS Code.', '',
           '### Sealed criteria', '', '| ID | Test | Met | What happened | Evidence |', '|---|---|---|---|---|']
    out += [f"| {c['id']} | {c['test']} | {'✅' if c['pass'] else '❌'} | {cell(c['did'])} | {c['evidence']} |" for c in R['criteria']]
    out += ['', '### Controls — good and bad data', '', '| Control | Data | Test | Should | Did | Message | Pass |', '|---|---|---|---|---|---|---|']
    out += [f"| {x['control']} | {x['data']} | {x['test']} | {x['should']} | {x['did']} | {cell(x['message'])} | {'✅' if x['pass'] else '❌'} |" for x in R['controls_tests']]
    out += ['', '### The run, step by step — as the agents issue the commands', '', '| # | Who | Command | Exit | Output |', '|---|---|---|---|---|']
    out += [f"| {i} | {s['who']} | `{cell(s['command'])}` | {s['exit']} | {cell(s['output'][:400])} |" for i, s in enumerate(R['steps'], 1)]
    return '\n'.join(out) + '\n'


def main():
    R = run(); write_evidence(R)
    text = DOC.read_text(encoding='utf-8')
    if '## Results' in text: text = text[:text.index('## Results')]
    text = text.replace('> **Status: plan.**', f"> **Status: run {R['date']} — criteria sealed before the run (spec commit 5cbb0ed; plan commit 84dc327).**")
    from sdem.docmap import relink
    DOC.write_text(relink(text.rstrip('\n') + '\n\n' + render(R), DOC), encoding='utf-8')
    print(render(R).split('\n')[2])
    import sdem.controls as sc; sc.main([])
    return 0 if all(c['pass'] for c in R['criteria']) and all(x['pass'] for x in R['controls_tests']) else 1


if __name__ == '__main__':
    raise SystemExit(main())
