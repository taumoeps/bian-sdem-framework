"""Organisation profiles (docs/design/sdem-profile-spec.md, PR-01…PR-12): an organisation's own design specification on top of SDEM's
metamodel — types extending SDEM's, attributes, rules, link kinds, names; a base profile shared by every team; checked, applied
everywhere a workspace is read, kept with the graph store; never a change to SDEM's own types. Synthetic data only."""
import json, os, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from sdem import profile as P  # noqa: E402

PAY = ROOT / 'examples' / 'payment-initiation'
ENV = {**os.environ, 'PYTHONPATH': str(ROOT) + os.pathsep + os.environ.get('PYTHONPATH', '')}


def sdem(*args, cwd, ok=(0,)):
    r = subprocess.run([sys.executable, '-m', 'sdem', *map(str, args)], cwd=cwd, capture_output=True, text=True, env=ENV)
    assert r.returncode in ok, f'sdem {" ".join(map(str, args))}: exit {r.returncode}\n{r.stdout[-900:]}\n{r.stderr[-900:]}'
    return r.returncode, r.stdout + r.stderr, (json.loads(r.stdout) if r.stdout.strip().startswith('{') else None)


def complete(ws):
    """Fill the bank's required attributes on every application of the example, so the data meets the bank base profile."""
    f = ws / 'a3-application.json'; d = json.loads(f.read_text())
    for i in d['instances']:
        if i['type'] == 'A3.ApplicationComponent':
            i.setdefault('attributes', {}).setdefault('owner', 'ROLE-PAY-OFFICER'); i['attributes'].setdefault('risk_tier', '2')
    f.write_text(json.dumps(d, indent=1))


class ProfileTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()); self.ws = self.tmp / 'ws'
        sdem('profile', 'example', '--out', self.tmp / 'profiles', cwd=self.tmp)
        sdem('new', '--workspace', self.ws, '--person', 'steven', '--example', 'payment-initiation', cwd=self.tmp)
        shutil.copy(self.tmp / 'profiles' / 'bank-base.json', self.ws / 'sdem-profile.json')

    def tearDown(self):
        P.deactivate(); shutil.rmtree(self.tmp, ignore_errors=True)

    def test_the_example_profiles_check_and_extend(self):  # PR-01, PR-02
        _, out, _ = sdem('profile', 'check', '--workspace', self.ws, cwd=self.tmp)
        self.assertIn('OK: profile bank-base', out)
        shutil.copy(self.tmp / 'profiles' / 'payments-team.json', self.ws / 'sdem-profile.json'); shutil.copy(self.tmp / 'profiles' / 'bank-base.json', self.ws / 'bank-base.json')
        _, out, d = sdem('profile', 'check', '--workspace', self.ws, '--json', cwd=self.tmp)
        self.assertEqual([c['name'] for c in d['chain']], ['bank-base', 'payments-team'])
        _, _, d = sdem('profile', 'show', '--workspace', self.ws, '--json', cwd=self.tmp)
        self.assertIn('BANK.A3.PaymentsGateway', [t['type'] for t in d['types']])                     # the team's type on top of the bank's
        self.assertEqual(d['names']['layers']['A3'], 'L3 Applications')                                # inherited from the base

    def test_the_bank_rules_apply_to_the_data(self):  # PR-03, PR-04
        code, out, _ = sdem('check', '--workspace', self.ws, cwd=self.tmp, ok=(1,))
        self.assertIn("BANK-R01 — every application names its owner and risk tier", out)
        self.assertIn("required attribute 'risk_tier' missing", out)
        complete(self.ws)
        self.assertEqual(sdem('check', '--workspace', self.ws, cwd=self.tmp)[0], 0)
        f = self.ws / 'a3-application.json'; d = json.loads(f.read_text())
        d['instances'].append({'id': 'APP-PAY-MS', 'type': 'BANK.A3.PaymentsMicroservice', 'version': '1', 'name': 'Payment notifications', 'lifecycle_status': 'active',
                               'attributes': {'owner': 'ROLE-PAY-OFFICER', 'risk_tier': '9', 'owning_team': 'payments-core'}})
        f.write_text(json.dumps(d))
        code, out, _ = sdem('check', '--workspace', self.ws, cwd=self.tmp, ok=(1,))
        self.assertIn("APP-PAY-MS: attribute 'risk_tier' value '9' is not one of ['1', '2', '3']", out)           # the bank's enum
        d['instances'][-1]['attributes']['risk_tier'] = '1'; f.write_text(json.dumps(d))
        code, out, _ = sdem('check', '--workspace', self.ws, cwd=self.tmp)
        self.assertNotIn('APP-PAY-MS', out)                                                            # a bank type, checked as an application

    def test_a_bank_type_is_an_application_to_the_engine_and_the_names_show(self):  # PR-06, PR-08
        complete(self.ws)
        f = self.ws / 'a3-application.json'; d = json.loads(f.read_text())
        d['instances'].append({'id': 'APP-PAY-MS', 'type': 'BANK.A3.PaymentsMicroservice', 'version': '1', 'name': 'Payment notifications', 'lifecycle_status': 'active',
                               'attributes': {'owner': 'ROLE-PAY-OFFICER', 'risk_tier': '1', 'owning_team': 'payments-core', 'deployed_on': ['INF-K8S-PAY-PROD']}})
        f.write_text(json.dumps(d))
        f4 = self.ws / 'a4-technology.json'; d4 = json.loads(f4.read_text())
        next(i for i in d4['instances'] if i['id'] == 'INF-K8S-PAY-PROD')['attributes']['hosts'].append('APP-PAY-MS'); f4.write_text(json.dumps(d4))   # the A4 side's evidence (S33)
        sdem('build', '--workspace', self.ws, '--out', self.ws / 'graph', cwd=self.tmp)
        self.assertTrue((self.ws / 'graph' / 'profile.json').exists())                                 # the store keeps the profile it was built with
        _, out, _ = sdem('trace', 'APP-PAY-HUB', '--direction', 'down', '--graph', self.ws / 'graph', cwd=self.tmp)
        self.assertIn('[L3 Applications · Application]', out)                                           # the bank's names
        _, out, _ = sdem('impact', 'INF-K8S-PAY-PROD', '--change', 'rehost', '--graph', self.ws / 'graph', cwd=self.tmp)
        self.assertIn('INF-K8S-PAY-PROD', out)
        _, _, d = sdem('link', '--workspace', self.ws, '--out', self.tmp / 'links', '--json', cwd=self.tmp)
        self.assertTrue(any(p['source'] == 'APP-PAY-MS' and p['relationship'] == 'DEPLOYED_ON' for p in d['proposals']))   # the engine links the bank's type like any application

    def test_a_bank_link_kind_inside_a_layer(self):  # PR-05
        complete(self.ws)
        f = self.ws / 'a4-technology.json'; d = json.loads(f.read_text())
        d['relationships'].append({'source': 'INF-K8S-PAY-PROD', 'kind': 'operated_by', 'target': 'INF-K8S-PAY-UAT'})   # A4.SystemSoftware is a Node
        f.write_text(json.dumps(d))
        code, out, _ = sdem('check', '--workspace', self.ws, cwd=self.tmp)
        self.assertNotIn('operated_by', out)
        d['relationships'].append({'source': 'INF-K8S-PAY-PROD', 'kind': 'made_up_kind', 'target': 'INF-K8S-PAY-UAT'}); f.write_text(json.dumps(d))
        code, out, _ = sdem('check', '--workspace', self.ws, cwd=self.tmp, ok=(1,))
        self.assertIn("'made_up_kind' is not catalogued", out)

    def test_a_profile_never_changes_sdem_itself(self):  # PR-02, PR-09
        bad = json.loads((self.tmp / 'profiles' / 'bank-base.json').read_text())
        bad['types'].append({'type': 'A3.ApplicationComponent', 'extends': 'A3.ApplicationComponent'})
        bad['types'].append({'type': 'BANK.A2.Thing', 'extends': 'A3.ApplicationComponent'})
        bad['link_kinds'].append({'kind': 'teleports', 'maps_to': 'teleportation', 'source_type': 'A4.Node', 'target_type': 'A4.Node'})
        (self.tmp / 'bad.json').write_text(json.dumps(bad))
        code, out, d = sdem('profile', 'check', '--file', self.tmp / 'bad.json', '--json', cwd=self.tmp, ok=(1,))
        self.assertTrue(any('redefines an SDEM type' in i for i in d['issues']))
        self.assertTrue(any('its layer is A2 but it extends an A3 type' in i for i in d['issues']))
        self.assertTrue(any("maps_to 'teleportation' is not an ArchiMate kind" in i for i in d['issues']))
        from sdem.metamodel import Metamodel
        self.assertNotIn('BANK.A3.PaymentsMicroservice', Metamodel.base().entities)                    # SDEM's metamodel is untouched
        other = self.tmp / 'plain'; sdem('new', '--workspace', other, '--person', 'steven', '--example', 'payment-initiation', cwd=self.tmp)
        _, out, _ = sdem('check', '--workspace', other, cwd=self.tmp)
        self.assertNotIn('BANK-R01', out)                                                              # a workspace without a profile is unaffected

    def test_a_requirement_traces_through_what_realises_it(self):  # the realization link (ArchiMate 3.2 ch. 6), followed by trace
        complete(self.ws)
        f = self.ws / 'a1-business.json'; d = json.loads(f.read_text())
        d['instances'].append({'id': 'BREQ-PAY-01', 'type': 'A1.BusinessRequirement', 'version': '1', 'name': 'Customers can submit a payment from the mobile app', 'lifecycle_status': 'active',
                               'attributes': {'requirement_kind': 'requirement', 'requirement_class': 'functional', 'regulatory_reference': 'none'}})   # ArchiMate's kind; the bank's class
        d['relationships'].append({'source': 'PRC-PAY-01', 'kind': 'realization', 'target': 'BREQ-PAY-01'})
        f.write_text(json.dumps(d))
        self.assertEqual(sdem('check', '--workspace', self.ws, cwd=self.tmp)[0], 0)
        sdem('build', '--workspace', self.ws, '--out', self.ws / 'graph', cwd=self.tmp)
        _, out, _ = sdem('trace', 'BREQ-PAY-01', '--direction', 'down', '--follow-composition', '--graph', self.ws / 'graph', cwd=self.tmp)
        for rid in ('PRC-PAY-01', 'SD-PI', 'APP-PAY-HUB', 'INF-K8S-PAY-PROD'): self.assertIn(rid, out)   # requirement → process → domain → application → platform

    def test_disaster_recovery_rules_are_conditional_and_cross_record(self):  # PR-10, PR-11
        complete(self.ws)
        f = self.ws / 'a4-technology.json'; d = json.loads(f.read_text())
        prod = next(i for i in d['instances'] if i['id'] == 'INF-K8S-PAY-PROD'); uat = next(i for i in d['instances'] if i['id'] == 'INF-K8S-PAY-UAT')
        def check(*expect, ok=True):
            f.write_text(json.dumps(d)); code, out, _ = sdem('check', '--workspace', self.ws, cwd=self.tmp, ok=(0,) if ok else (1,))
            for e in expect: self.assertIn(e, out)
            return out
        self.assertNotIn('BANK-DR', check())                                                           # no environment stated: the DR rules do not apply
        prod['attributes']['environment'] = 'production'
        check('INF-K8S-PAY-PROD: BANK-DR01 — every production platform states its DR tier, region and replication', ok=False)
        uat['attributes']['environment'] = 'non_production'
        self.assertNotIn('INF-K8S-PAY-UAT: BANK-DR01', check(ok=False))                              # the condition: production only
        prod['attributes'].update(dr_tier='3', dr_region='region-a', replication_mode='async')
        self.assertNotIn('BANK-DR', check())                                                           # tier 3 needs no DR pair
        prod['attributes']['dr_tier'] = '1'
        check('INF-K8S-PAY-PROD: BANK-DR02 — a tier 1 or 2 production platform has a DR pair (bank resilience standard §5.2): 0 dr_pair_of link(s), needs at least 1', ok=False)
        uat['attributes']['dr_region'] = 'region-a'
        d['relationships'].append({'source': 'INF-K8S-PAY-PROD', 'kind': 'dr_pair_of', 'target': 'INF-K8S-PAY-UAT'})
        check("BANK-DR03 — a platform and its DR pair run in different regions (bank resilience standard §5.3): dr_region is 'region-a' here and 'region-a' on INF-K8S-PAY-UAT (dr_pair_of) — must differ", ok=False)
        uat['attributes']['dr_region'] = 'region-b'
        self.assertNotIn('BANK-DR', check())                                                           # paired, in another region: all three rules hold

    def test_the_organisation_adds_requirement_categories(self):  # PR-12
        complete(self.ws)
        f = self.ws / 'requirements.json'; d = json.loads(f.read_text())
        d['requirements'][0]['category'] = 'operational_resilience'; f.write_text(json.dumps(d))
        _, out, _ = sdem('check', '--workspace', self.ws, cwd=self.tmp)
        self.assertIn('OK: requirements', out)
        (self.ws / 'sdem-profile.json').unlink()
        code, out, _ = sdem('check', '--workspace', self.ws, cwd=self.tmp, ok=(1,))
        self.assertIn('category: must be one of', out)                                                 # not one of SDEM's without the profile
        bad = json.loads((self.tmp / 'profiles' / 'bank-base.json').read_text())
        bad['requirement_categories'].append({'id': 'availability'})
        bad['rules'].append({'id': 'X', 'entity': 'A4.Node', 'when': {'no_such_field': 'x'}, 'link': {'kind': 'no_such_kind'}})
        (self.tmp / 'bad.json').write_text(json.dumps(bad))
        _, _, r = sdem('profile', 'check', '--file', self.tmp / 'bad.json', '--json', cwd=self.tmp, ok=(1,))
        self.assertTrue(any("availability: already one of SDEM's" in i for i in r['issues']))
        self.assertTrue(any("when 'no_such_field'" in i for i in r['issues']))
        self.assertTrue(any("link kind 'no_such_kind'" in i for i in r['issues']))

    def test_a_baseline_carries_its_profile_and_the_record_says_so(self):  # PR-07
        complete(self.ws)
        nw = self.tmp / 'nw'
        _, _, d = sdem('new', '--workspace', nw, '--person', 'steven', '--from', self.ws, '--json', cwd=self.tmp)
        self.assertTrue((nw / 'sdem-profile.json').exists()); self.assertEqual(d['profile']['from'], 'baseline')
        self.assertEqual(sdem('check', '--workspace', nw, '--require-recorded', cwd=self.tmp)[0], 0)


if __name__ == '__main__':
    unittest.main()
