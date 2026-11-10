"""An organisation above its workspaces (docs/design/sdem-workspace-spec.md WS-08…WS-10): `sdem new --organisation NAME` starts the
folder with a starter base profile; a workspace started in it gets its own profile extending that base — named with
`--organisation`, or found by looking upward; a workspace outside the organisation, an unknown organisation, or an organisation
inside another is refused. Made-up names only."""
import json, os, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sdem(*args, cwd):
    env = {**os.environ, 'PYTHONPATH': str(ROOT) + os.pathsep + os.environ.get('PYTHONPATH', '')}   # installed or not (CI is not)
    r = subprocess.run([sys.executable, '-m', 'sdem', *map(str, args)], cwd=cwd, capture_output=True, text=True, env=env)
    return r.returncode, r.stdout + r.stderr


class OrganisationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        code, out = sdem('new', '--organisation', 'bank-xyz', '--person', 'jane.architect', cwd=self.tmp)
        self.assertEqual(code, 0, out); self.org = self.tmp / 'bank-xyz'

    def tearDown(self): shutil.rmtree(self.tmp, ignore_errors=True)

    def test_an_organisation_starts_with_a_base_profile_that_passes_its_check(self):   # WS-08
        rec = json.loads((self.org / 'sdem-organisation.json').read_text())
        self.assertEqual((rec['name'], rec['created_by'], rec['base_profile']), ('bank-xyz', 'jane.architect', 'profiles/bank-xyz-base.json'))
        self.assertTrue((self.org / 'workspaces').is_dir())
        code, out = sdem('profile', 'check', '--file', 'bank-xyz/profiles/bank-xyz-base.json', cwd=self.tmp)
        self.assertEqual(code, 0, out); self.assertIn('OK: profile bank-xyz-base', out)

    def test_a_workspace_named_with_its_organisation_extends_the_base(self):   # WS-09, WS-10
        code, out = sdem('new', '--workspace', 'workspaces/ledger', '--organisation', 'bank-xyz', '--person', 'jane.architect', cwd=self.tmp)
        self.assertEqual(code, 0, out)
        self.assertIn('organisation bank-xyz — profile bank-xyz-base → bank-xyz-ledger v1', out)
        ws = self.org / 'workspaces' / 'ledger'
        self.assertEqual(json.loads((ws / 'sdem-profile.json').read_text())['extends'], '../../profiles/bank-xyz-base.json')
        rec = json.loads((ws / 'workspace.json').read_text())
        self.assertEqual(rec['organisation']['name'], 'bank-xyz'); self.assertEqual(rec['profile']['chain'], ['bank-xyz-base', 'bank-xyz-ledger'])

    def test_the_base_profile_applies_to_the_workspace(self):   # WS-10: the organisation's rules reach sdem check
        base = self.org / 'profiles' / 'bank-xyz-base.json'; doc = json.loads(base.read_text())
        doc['attributes'] = [{'entity': 'A3.ApplicationComponent', 'name': 'risk_tier', 'type': 'enum', 'values': ['1', '2', '3'], 'required': True}]
        base.write_text(json.dumps(doc))
        self.assertEqual(sdem('new', '--workspace', 'workspaces/ledger', '--organisation', 'bank-xyz', '--person', 'jane.architect', cwd=self.tmp)[0], 0)
        a3 = self.org / 'workspaces' / 'ledger' / 'a3-application.json'; d = json.loads(a3.read_text())
        d['instances'] = [{'id': 'APP-GL', 'type': 'A3.ApplicationComponent', 'version': '1', 'name': 'General ledger', 'lifecycle_status': 'active',
                           'description': 'made up', 'attributes': {}}]
        a3.write_text(json.dumps(d))
        code, out = sdem('check', '--workspace', 'bank-xyz/workspaces/ledger', cwd=self.tmp)
        self.assertNotEqual(code, 0); self.assertIn("required attribute 'risk_tier' missing", out)

    def test_inside_the_organisation_it_is_found_without_the_option(self):   # WS-09
        code, out = sdem('new', '--workspace', 'workspaces/payments', '--person', 'jane.architect', cwd=self.org)
        self.assertEqual(code, 0, out); self.assertIn('organisation bank-xyz', out)
        self.assertTrue((self.org / 'workspaces' / 'payments' / 'sdem-profile.json').exists())
        code, out = sdem('new', '--workspace', 'workspaces/cards', '--organisation', 'bank-xyz', '--person', 'jane.architect', cwd=self.org / 'workspaces')
        self.assertEqual(code, 0, out); self.assertTrue((self.org / 'workspaces' / 'cards' / 'workspace.json').exists())   # from the organisation's folder

    def test_what_is_refused(self):   # WS-08, WS-09
        cases = [(('new', '--workspace', '../outside', '--organisation', 'bank-xyz'), 'not inside the organisation bank-xyz'),
                 (('new', '--workspace', 'workspaces/x', '--organisation', 'bank-abc'), 'no such organisation'),
                 (('new', '--organisation', 'bank-xyz'), 'already exists and is not empty'),
                 (('new', '--organisation', 'bank-xyz/sub'), 'not started inside another'),
                 (('new', '--organisation', 'bank-new', '--profile', 'x.json'), 'are for a workspace')]
        for args, msg in cases:
            code, out = sdem(*args, '--person', 'jane.architect', cwd=self.tmp)
            self.assertEqual(code, 2, (args, out)); self.assertIn(msg, out)
        self.assertFalse((self.tmp / 'outside').exists()); self.assertFalse((self.tmp / 'bank-abc').exists())

    def test_an_explicit_profile_wins(self):   # WS-10
        code, out = sdem('new', '--workspace', 'workspaces/team', '--organisation', 'bank-xyz', '--person', 'jane.architect',
                         '--profile', ROOT / 'examples' / 'profiles' / 'payments-team.json', cwd=self.tmp)
        self.assertEqual(code, 0, out); self.assertIn('profile bank-base → payments-team v1 (from ', out)

    def test_a_dry_run_writes_nothing(self):
        code, out = sdem('new', '--organisation', 'bank-dry', '--person', 'jane.architect', '--dry-run', '--json', cwd=self.tmp)
        self.assertEqual(code, 0, out); self.assertEqual(json.loads(out)['name'], 'bank-dry'); self.assertFalse((self.tmp / 'bank-dry').exists())
        code, out = sdem('new', '--workspace', 'workspaces/l', '--organisation', 'bank-xyz', '--person', 'jane.architect', '--dry-run', cwd=self.tmp)
        self.assertEqual(code, 0, out); self.assertFalse((self.org / 'workspaces' / 'l').exists())


if __name__ == '__main__':
    unittest.main()
