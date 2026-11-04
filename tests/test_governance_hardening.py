"""v0.11.2 governance hardening (docs/design/sdem-governance.md; RR-E06): current against proposed compliance, human decisions that a
typed name cannot verify, a governed baseline, and multi-value options. Tests A–F of the owner's hardening brief, on synthetic data:
Phase A — the non-compliant target (the payments example); Phase B — a compliant target that remediates four current breaches."""
import json, os, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from sdem import agents, governance, requirements as R  # noqa: E402

PAY = ROOT / 'examples' / 'payment-initiation'
REHOST = ROOT / '.github' / 'skills' / 'sdem-change-sets' / 'example-a4-rehost.json'
AGENT = {'A1': 'sdem-a1-business', 'A2': 'sdem-a2-bian', 'A3': 'sdem-a3-application', 'A4': 'sdem-a4-technology'}
ORCH, P, HUMAN = 'sdem-orchestrator', 'steven.human', 'steven@example.org'
CE = agents.CoordinationError
ENV = {**os.environ, 'PYTHONPATH': str(ROOT) + os.pathsep + os.environ.get('PYTHONPATH', '')}


def sdem(*args, cwd=None, ok=(0,)):
    r = subprocess.run([sys.executable, '-m', 'sdem', *map(str, args)], capture_output=True, text=True, env=ENV, cwd=cwd)
    assert r.returncode in ok, f'sdem {" ".join(map(str, args))}: exit {r.returncode}\n{r.stdout[-700:]}\n{r.stderr[-700:]}'
    return r.returncode, (json.loads(r.stdout) if r.stdout.strip().startswith('{') else r.stdout + r.stderr)


def phase_b(reg):
    """The Phase B registry: every requirement met by the proposed platform; four breached today (synthetic)."""
    cond = {'REQ-AV-01': 99.99, 'REQ-AV-02': 99.99, 'REQ-PF-01': 240, 'REQ-RT-01': 1.5, 'REQ-RC-01': '1.5h', 'REQ-CAP-01': 3.5}
    for r in reg['requirements']:
        if r['id'] in cond: r['condition']['value'] = cond[r['id']]
        if r['status'] == 'proposed': r['status'] = 'confirmed'; r['history'].append({'version': 1, 'status': 'confirmed', 'by': P, 'at': '2026-11-01T00:00:00+00:00'})
    M = [('INF-K8S-PAY-PROD', 'availability_pct', 99.97, '%', 'current'), ('INF-K8S-PAY-PROD2', 'availability_pct', 99.995, '%', 'proposed'),
         ('APP-PAY-HUB', 'p95_latency', 220, 'ms', 'current'), ('APP-PAY-HUB', 'p95_latency', 230, 'ms', 'proposed'),
         ('INF-K8S-PAY-PROD', 'region', 'XA', '', 'current'), ('INF-K8S-PAY-PROD2', 'region', 'XA', '', 'proposed'),
         ('INF-K8S-PAY-PROD', 'event_streaming', True, '', 'current'), ('INF-K8S-PAY-PROD2', 'event_streaming', True, '', 'proposed'),
         ('APP-PAY-HUB', 'recovery_time', '1h', '', 'current'), ('APP-PAY-HUB', 'recovery_time', '1.5h', '', 'proposed'),
         ('INF-K8S-PAY-PROD', 'second_region_replica', True, '', 'current'), ('INF-K8S-PAY-PROD2', 'second_region_replica', True, '', 'proposed'),
         ('INF-K8S-PAY-PROD', 'peak_factor', 3.2, '', 'current'), ('INF-K8S-PAY-PROD2', 'peak_factor', 3.5, '', 'proposed'),
         ('SD-PE', 'execution_time', 1.8, 's', 'current'), ('SD-PE', 'execution_time', 1.5, 's', 'proposed'),
         ('PRC-PAY-01', 'availability_pct', 99.96, '%', 'current'), ('PRC-PAY-01', 'availability_pct', 99.99, '%', 'proposed'),
         ('PRC-PAY-02', 'region', 'XA', '', 'current'), ('PRC-PAY-02', 'region', 'XA', '', 'proposed')]
    reg['measurements'] = [{'id': f'MEAS-{n:03d}', 'record': r, 'metric': m, 'value': v, **({'unit': u} if u else {}), 'state': s, 'evidence': [f'synthetic:{n}'],
                            'provenance': {'by': P, 'at': '2026-11-01T00:00:00+00:00'}} for n, (r, m, v, u, s) in enumerate(M, 1)]
    return reg


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()); self.ws = self.tmp / 'ws'
        shutil.copytree(PAY, self.ws, ignore=shutil.ignore_patterns('graph', 'coordination', 'migrations'))
        self.e = agents.Estate(self.ws)

    def tearDown(self): shutil.rmtree(self.tmp, ignore_errors=True)

    def rehost_and_assess(self):
        self.e.propose(json.loads(REHOST.read_text()), AGENT['A4'], P)
        v, _ = self.e.request_validation('CE-001', ORCH, P)
        for l in ('A1', 'A2', 'A3', 'A4'):
            c = v['layers'][l]['calculated']
            if c['classification'] == 'no_impact':
                self.e.assess('CE-001', l, 'no_impact_confirmed', AGENT[l], P, 'checked', evidence=[f'review:{l}'], uncertainty='gaps off path')
            else:
                self.e.assess('CE-001', l, 'impact_confirmed', AGENT[l], P, 'checked', evidence=[f'review:{l}'], records=[r['id'] for r in c['records']])
        return self.e.validation('CE-001')

    def disp(self, an): return {e['requirement']: e['disposition'] for e in an['requirements']}


class TestA_NonCompliantTarget(Base):
    def test_four_proposed_breaches_are_governed(self):
        v = self.rehost_and_assess(); an = v['analysis']
        self.assertEqual(an['contract'], R.CONTRACT)
        self.assertEqual(sorted(k for k, d in self.disp(an).items() if d == 'proposed_breach'), ['REQ-AV-02', 'REQ-RC-02', 'REQ-RES-02', 'REQ-RT-02'])
        breaches = [f['id'] for f in an['risks'] if f['type'] == 'confirmed_breach']
        self.assertEqual(len(breaches), 4); self.assertTrue(all('introduced by the change' in f['text'] for f in an['risks'] if f['type'] == 'confirmed_breach'))
        with self.assertRaises(CE): self.e.accept_validation('CE-001', P, 'ok', authorise=True)        # blocked until each breach is decided
        with self.assertRaises(CE): self.e.plan('CE-001', ORCH, P)

    def test_prior_assessments_go_stale_on_reanalysis(self):
        self.rehost_and_assess()
        sdem('requirements', 'measure', '--record', 'APP-PAY-HUB', '--metric', 'p95_latency', '--value', '250', '--unit', 'ms', '--state', 'proposed',
             '--evidence', 'test:PT-1', '--workspace', self.ws, '--person', P)
        self.e.analyse('CE-001', ORCH, P)
        code, d = sdem('events', 'show', 'CE-001', '--workspace', self.ws, '--json')
        self.assertTrue(all(r['stale'] for r in d['summary']['layers'].values()))

    def test_assessments_against_an_earlier_contract_are_stale_after_reanalysis(self):   # a v0.11.1 validation re-analysed: same evidence, new reading
        self.rehost_and_assess()
        f = self.ws / 'coordination' / 'validations' / 'IV-001.json'; x = json.loads(f.read_text())
        x['analysis'].pop('contract')
        for l in x['layers'].values():
            for s in l['assessments']: s.pop('analysis_contract', None)
        f.write_text(json.dumps(x))
        self.e.analyse('CE-001', ORCH, P)
        code, d = sdem('events', 'show', 'CE-001', '--workspace', self.ws, '--json')
        self.assertTrue(all(r['stale'] for r in d['summary']['layers'].values()))
        breaches = [g['id'] for g in self.e.validation('CE-001')['analysis']['risks'] if g['type'] == 'confirmed_breach']
        with self.assertRaises(CE) as c: self.e.accept_validation('CE-001', P, 'ok', authorise=True, accept_risks={b: 'r' for b in breaches})
        self.assertIn('re-assess', str(c.exception))

    def test_an_analysis_from_before_v0_11_2_is_not_reinterpreted(self):
        v = self.rehost_and_assess()
        f = self.ws / 'coordination' / 'validations' / 'IV-001.json'; x = json.loads(f.read_text()); x['analysis'].pop('contract'); f.write_text(json.dumps(x))
        with self.assertRaises(CE) as c: self.e.accept_validation('CE-001', P, 'ok', authorise=True, accept_risks={'RF-BREACH-REQ-AV-02': 'r'})
        self.assertIn('RR-E06', str(c.exception))


class TestB_CompliantTarget(Base):
    def setUp(self):
        super().setUp(); R.save(self.ws, phase_b(R.load(self.ws)))

    def test_remediated_current_breaches_are_not_proposed_breaches(self):
        v = self.rehost_and_assess(); an = v['analysis']; d = self.disp(an)
        self.assertEqual(sorted(k for k, x in d.items() if x == 'current_breach_remediated'), ['REQ-AV-01', 'REQ-AV-02', 'REQ-CAP-01', 'REQ-RT-01'])
        self.assertEqual(sum(1 for e in an['requirements'] if e['proposed']['result'] == 'satisfied'), 10)
        self.assertEqual({e['overall'] for e in an['requirements']}, {'satisfied'})
        self.assertFalse([f for f in an['risks'] if f['type'] == 'confirmed_breach'])                # no false proposed-state breach
        self.assertEqual(len([f for f in an['risks'] if f['type'] == 'remediated_breach']), 4)       # the history stays visible
        self.e.accept_validation('CE-001', P, 'compliant target', authorise=True)                    # no --accept-risk needed
        self.assertTrue(self.e.plan('CE-001', ORCH, P)['work_items'])


class TestC_MissingProposedEvidence(Base):
    def test_no_proposed_evidence_is_not_compliance(self):
        reg = phase_b(R.load(self.ws)); reg['measurements'] = [m for m in reg['measurements'] if not (m['record'] == 'APP-PAY-HUB' and m['metric'] == 'p95_latency' and m['state'] == 'proposed')]
        R.save(self.ws, reg)
        an = self.rehost_and_assess()['analysis']
        e = next(x for x in an['requirements'] if x['requirement'] == 'REQ-PF-01')
        self.assertEqual((e['disposition'], e['overall']), ('missing_evidence', 'missing_evidence'))
        f = [x for x in an['risks'] if x.get('requirement') == 'REQ-PF-01']
        self.assertTrue(any(x['type'] == 'missing_evidence' and x['decision'] for x in f))


@unittest.skipIf(os.name == 'nt' or not shutil.which('ssh-keygen'), 'SSH commit signing via ssh-keygen (POSIX CI)')
class TestD_HumanGovernanceBypass(Base):
    """An agent can type a person's name; it cannot sign as that person. Verification and the fail-closed gate rest on the signature."""
    def setUp(self):
        super().setUp()
        self.repo = self.tmp; self.git('init', '-q'); self.git('config', 'user.email', 'agent@example.org'); self.git('config', 'user.name', 'agent')
        for who in ('human', 'agent'):
            subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-C', who, '-f', str(self.tmp / f'{who}_key')], check=True)
        pub = (self.tmp / 'human_key.pub').read_text().split()
        (self.tmp / 'allowed_signers').write_text(f'{HUMAN} namespaces="git" {pub[0]} {pub[1]}\n')
        (self.ws / 'governance.json').write_text(json.dumps({'require_verified_decisions': True, 'allowed_signers': '../allowed_signers',
                                                              'approvers': [{'person': P, 'signer': HUMAN}]}))
        self.git('add', '-A'); self.commit('baseline', None)

    def git(self, *a): return subprocess.run(['git', *a], cwd=self.repo, capture_output=True, text=True, check=True)

    def commit(self, msg, key):
        self.git('add', '-A')
        sign = ['-c', 'gpg.format=ssh', '-c', f'user.signingkey={self.tmp / (key + "_key")}', 'commit', '-q', '-S'] if key else ['commit', '-q']
        subprocess.run(['git', *sign, '-m', msg], cwd=self.repo, capture_output=True, text=True, check=True)

    def statuses(self): return {r['kind']: r['status'] for r in governance.verify(self.ws)}

    def test_an_agent_typing_the_human_name_gets_no_authority(self):
        self.rehost_and_assess()
        breaches = [f['id'] for f in self.e.validation('CE-001')['analysis']['risks'] if f['type'] == 'confirmed_breach']
        # the agent runs every governed command with the human's name — no --agent anywhere
        sdem('events', 'accept', 'CE-001', '--reason', 'agent', '--authorise', '--accept-risk', *[f'{b}=agent' for b in breaches], '--workspace', self.ws, '--person', P, '--json')
        sdem('requirements', 'confirm', 'REQ-CAP-01', '--workspace', self.ws, '--person', P, '--json')
        acc = self.e.validation('CE-001')['acceptance']
        self.assertEqual(acc['attestation'], 'attributed'); self.assertTrue(acc['decisions'])                          # recorded as a claim, nothing more
        self.commit('agent commits', None)                                                                            # unsigned
        self.assertEqual(self.statuses()['accept_impact'], 'unsigned_or_invalid')
        with self.assertRaises(CE) as c: self.e.plan('CE-001', ORCH, P)                                               # fail closed
        self.assertIn('GV-04', str(c.exception))
        code, d = sdem('governance', 'verify', '--workspace', self.ws, '--require-verified', '--json', ok=(1,))
        self.assertGreater(d['unverified'], 0)

    def test_the_agents_own_signature_does_not_verify_the_human(self):
        self.rehost_and_assess()
        breaches = [f['id'] for f in self.e.validation('CE-001')['analysis']['risks'] if f['type'] == 'confirmed_breach']
        self.e.accept_validation('CE-001', P, 'agent', authorise=True, accept_risks={b: 'agent' for b in breaches})
        self.commit('agent signs', 'agent')
        self.assertEqual(self.statuses()['accept_impact'], 'unsigned_or_invalid')                                    # not an allowed signer
        with self.assertRaises(CE): self.e.plan('CE-001', ORCH, P)

    def test_approve_and_connect_with_a_human_name_stay_unverified(self):
        sdem('link', '--workspace', self.ws, '--out', self.ws / 'links', '--json')
        props = json.loads((self.ws / 'links' / 'proposals.json').read_text())['mappings']
        conn = sdem('connect', 'SD-PE', 'REALIZED_BY', 'CMP-PAY-EXEC', '--workspace', self.ws, '--person', P, '--evidence', 'application_architecture_document:AA-EXEC#2',
                    '--rationale', 'the gateway executes payments', '--json', ok=(0, 1))
        self.commit('agent', None)
        kinds = {r['kind']: r['status'] for r in governance.verify(self.ws)}
        if conn[0] == 0: self.assertEqual(kinds['state_link'], 'unsigned_or_invalid')
        self.assertTrue(all(s != 'verified' for s in kinds.values()))

    def test_the_humans_signed_commit_verifies_and_opens_the_gate(self):
        self.rehost_and_assess()
        breaches = [f['id'] for f in self.e.validation('CE-001')['analysis']['risks'] if f['type'] == 'confirmed_breach']
        self.e.accept_validation('CE-001', P, 'decided', authorise=True, accept_risks={b: 'decided' for b in breaches})
        self.commit('steven accepts CE-001', 'human')
        st = self.statuses()
        self.assertEqual((st['accept_impact'], st['authorise_implementation'], st['accept_residual_risk']), ('verified', 'verified', 'verified'))
        self.assertTrue(self.e.plan('CE-001', ORCH, P)['work_items'])

    def test_a_name_that_is_not_an_approver_never_verifies(self):
        self.rehost_and_assess()
        breaches = [f['id'] for f in self.e.validation('CE-001')['analysis']['risks'] if f['type'] == 'confirmed_breach']
        self.e.accept_validation('CE-001', 'someone.else', 'x', authorise=True, accept_risks={b: 'x' for b in breaches})
        self.commit('signed by the human key, wrong name', 'human')
        self.assertEqual(self.statuses()['accept_impact'], 'not_an_approver')


class TestE_WorkspaceBaseline(Base):
    def test_a_baseline_is_recorded_and_edits_after_it_are_noticed(self):
        nw = self.tmp / 'fresh'
        code, d = sdem('new', '--workspace', nw, '--person', P, '--from', PAY, '--json')
        self.assertEqual(sdem('check', '--workspace', nw, '--require-recorded', '--json')[1]['ok'], True)   # the ledger matches the baseline
        rec = json.loads((nw / 'workspace.json').read_text()); self.assertIn('requirements.json', rec['baseline']['files'])
        self.assertEqual([g['kind'] for g in governance.decisions(nw)], ['establish_baseline'])
        self.assertIn('baseline', json.loads((nw / 'sdem-ledger.json').read_text())['files']['a3-application.json']['by'])
        code, d = sdem('new', '--workspace', nw, '--person', P, '--from', PAY, ok=(2,))                    # never re-baselined
        a3 = json.loads((nw / 'a3-application.json').read_text()); a3['instances'][0]['name'] += ' (edited)'; (nw / 'a3-application.json').write_text(json.dumps(a3))
        code, d = sdem('check', '--workspace', nw, '--require-recorded', '--json', ok=(1,))
        self.assertEqual([u['file'] for u in d['unrecorded_edits']], ['a3-application.json'])

    def test_reconciling_a_copied_workspace_keeps_its_history(self):
        nw = self.tmp / 'phaseb'
        sdem('new', '--workspace', nw, '--person', P, '--json')                                           # empty layers in the ledger
        for f in ('a1-business.json', 'a2-service-domain.json', 'a3-application.json', 'a4-technology.json', 'mappings.json'):
            shutil.copy(PAY / f, nw / f)                                                                 # copied in by hand, as in Phase B
        e = agents.Estate(nw); e.propose(json.loads(REHOST.read_text()), AGENT['A4'], P)                 # CS-001 / CE-001
        code, d = sdem('check', '--workspace', nw, '--json')
        self.assertEqual(sorted(u['file'] for u in d['unrecorded_edits']), ['a1-business.json', 'a2-service-domain.json', 'a3-application.json', 'mappings.json'])
        for layer in ('A1', 'A2', 'A3', 'registry'):
            sdem('change', 'adopt', '--workspace', nw, '--layer', layer, '--person', P, '--reason', 'baseline copied in before the ledger knew it', '--json')
        self.assertEqual(sdem('check', '--workspace', nw, '--require-recorded', '--json')[1]['ok'], True)
        self.assertTrue((nw / 'coordination' / 'change-sets' / 'CS-001.json').exists())                    # history preserved
        self.assertEqual(sorted(g['subject'] for g in governance.decisions(nw) if g['kind'] == 'adopt_edit'),
                         ['a1-business.json', 'a2-service-domain.json', 'a3-application.json', 'mappings.json'])
        code, d = sdem('change', 'adopt', '--workspace', nw, '--layer', 'registry', '--person', 'sdem-a4-technology', '--reason', 'x', '--json', ok=(1, 2))
        self.assertEqual(d['error']['code'], 'needs_person')


class TestF_MultiValueOptions(Base):
    def test_repeated_options_keep_every_value(self):
        self.e.propose(json.loads(REHOST.read_text()), AGENT['A4'], P); self.e.request_validation('CE-001', ORCH, P)
        sdem('events', 'assess', 'CE-001', '--layer', 'A2', '--status', 'further_investigation_required',
             '--missing', 'SD-PE REALIZED_BY CMP-PAY-EXEC', '--missing', 'SO-PI-06 IMPLEMENTED_BY', '--missing', 'BBO-PARTY MAPPED_TO',
             '--evidence', 'a:1', '--evidence', 'b:2', '--mapping', 'PAY-106', '--mapping', 'PAY-107', '--reasoning', 'gaps',
             '--workspace', self.ws, '--agent', AGENT['A2'], '--person', P, '--json')
        a = self.e.validation('CE-001')['layers']['A2']['assessments'][-1]
        self.assertEqual(len(a['missing_relationships']), 3); self.assertEqual(a['evidence'], ['a:1', 'b:2']); self.assertEqual(a['mappings'], ['PAY-106', 'PAY-107'])

    def test_the_old_form_still_works(self):
        self.e.propose(json.loads(REHOST.read_text()), AGENT['A4'], P); self.e.request_validation('CE-001', ORCH, P)
        sdem('events', 'assess', 'CE-001', '--layer', 'A3', '--status', 'impact_confirmed', '--record', 'APP-PAY-HUB', 'CMP-PAY-EXEC', '--evidence', 'x:1', 'y:2',
             '--reasoning', 'r', '--workspace', self.ws, '--agent', AGENT['A3'], '--person', P, '--json')
        a = self.e.validation('CE-001')['layers']['A3']['assessments'][-1]
        self.assertEqual((a['records'], a['evidence']), (['APP-PAY-HUB', 'CMP-PAY-EXEC'], ['x:1', 'y:2']))


if __name__ == '__main__':
    unittest.main()
