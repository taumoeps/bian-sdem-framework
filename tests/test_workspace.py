"""Starting and shaping a workspace (docs/design/sdem-workspace-spec.md, WS-*): `sdem new` starts it with a BIAN layer; `sdem load`
needs it; `sdem bian custom` narrows one workspace's BIAN layer; `sdem bian update --root` keeps a workspace's own selection;
`sdem aid project --workspace` plans from it, kept apart in plans/."""
import json, os, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
EX = ROOT / 'examples' / 'payment-initiation'


def sdem(*args, cwd):
    env = {**os.environ, 'PYTHONPATH': str(ROOT) + os.pathsep + os.environ.get('PYTHONPATH', '')}   # installed or not (CI is not)
    r = subprocess.run([sys.executable, '-m', 'sdem', *map(str, args)], cwd=cwd, capture_output=True, text=True, env=env)
    return r.returncode, r.stdout + r.stderr


class WorkspaceTests(unittest.TestCase):
    def setUp(self): self.tmp = Path(tempfile.mkdtemp())
    def tearDown(self): shutil.rmtree(self.tmp, ignore_errors=True)

    def a2(self, ws): return json.loads((self.tmp / ws / 'a2-service-domain.json').read_text())
    def sds(self, ws): return [i for i in self.a2(ws)['instances'] if i['type'] == 'A2.ServiceDomain']

    def test_new_starts_with_the_full_base_bian_and_records_it(self):  # WS-01, WS-02
        code, out = sdem('new', '--workspace', 'workspaces/payments', '--person', 'jane.architect', cwd=self.tmp)
        self.assertEqual(code, 0, out)
        ws = self.tmp / 'workspaces' / 'payments'
        self.assertEqual(sorted(p.name for p in ws.iterdir()),
                         ['a1-business.json', 'a2-service-domain.json', 'a3-application.json', 'a4-technology.json', 'mappings.json', 'workspace.json'])
        self.assertEqual(len(self.sds('workspaces/payments')), 258)
        rec = json.loads((ws / 'workspace.json').read_text())
        self.assertEqual((rec['created_by'], rec['bian']['selection'], rec['bian']['service_domains']), ('jane.architect', 'all', 258))
        self.assertEqual(sdem('check', '--workspace', ws, cwd=self.tmp)[0], 0)
        code, out = sdem('new', '--workspace', 'workspaces/payments', '--person', 'jane.architect', cwd=self.tmp)   # started once
        self.assertEqual(code, 2); self.assertIn('already exists', out)
        code, out = sdem('new', '--workspace', 'workspaces/x', '--person', 'sdem-agent', cwd=self.tmp)
        self.assertEqual(code, 2); self.assertIn('person', out)

    def test_new_uses_the_shared_bian_layer_when_there_is_one(self):  # WS-01
        (self.tmp / 'bian').mkdir(); shutil.copy(EX / 'a2-service-domain.json', self.tmp / 'bian' / 'a2-service-domain.json')
        self.assertEqual(sdem('new', '--workspace', 'workspaces/payments', '--person', 'jane.architect', cwd=self.tmp)[0], 0)
        self.assertEqual(self.a2('workspaces/payments'), json.loads((EX / 'a2-service-domain.json').read_text()))
        code, out = sdem('new', '--workspace', 'workspaces/plain', '--person', 'jane.architect', '--no-bian', cwd=self.tmp)
        self.assertEqual(code, 0, out); self.assertFalse((self.tmp / 'workspaces' / 'plain' / 'a2-service-domain.json').exists())

    def test_load_needs_a_workspace(self):  # WS-03
        code, out = sdem('load', ROOT / 'tests' / 'fixtures', '--workspace', 'workspaces/none', '--person', 'jane.architect', '--all', cwd=self.tmp)
        self.assertNotEqual(code, 0); self.assertIn('sdem new --workspace workspaces/none', out)

    def test_custom_narrows_one_workspace_and_update_keeps_it(self):  # WS-04
        for w in ('payments', 'lending'): self.assertEqual(sdem('new', '--workspace', f'workspaces/{w}', '--person', 'jane.architect', cwd=self.tmp)[0], 0)
        code, out = sdem('bian', 'custom', '--workspace', 'workspaces/payments', '--only', 'Payment Order Initiation', 'Term Deposit', '--person', 'jane.architect', cwd=self.tmp)
        self.assertEqual(code, 0, out); self.assertIn('narrowed the BIAN layer to 2', out)
        self.assertEqual(sorted(i['name'] for i in self.sds('workspaces/payments')), ['Payment Order Initiation', 'Term Deposit'])
        rec = json.loads((self.tmp / 'workspaces' / 'payments' / 'workspace.json').read_text())['bian']
        self.assertEqual((rec['selection'], rec['chosen'], rec['changed_by']), ('custom', ['Payment Order Initiation', 'Term Deposit'], 'jane.architect'))
        self.assertTrue((self.tmp / 'workspaces' / 'payments' / 'bian-updates' / 'BU-001.json').exists())
        (self.tmp / 'bian').mkdir(); self.assertEqual(sdem('bian', 'import', '--base', '--only', 'Payment Rail', '-o', 'bian/a2-service-domain.json', cwd=self.tmp)[0], 0)
        code, out = sdem('bian', 'update', '--root', 'workspaces', '--a2', 'bian/a2-service-domain.json', '--person', 'sdem.lead', cwd=self.tmp)
        self.assertEqual(code, 0, out); self.assertIn('workspaces/payments: has its own BIAN selection', out)
        self.assertEqual(len(self.sds('workspaces/payments')), 2)                              # kept
        self.assertEqual([i['name'] for i in self.sds('workspaces/lending')], ['Payment Rail'])  # the others follow the shared layer

    def test_custom_never_strands_an_approved_connection(self):  # WS-04 (BU-03)
        shutil.copytree(EX, self.tmp / 'workspaces' / 'pay', ignore=shutil.ignore_patterns('graph', 'migrations'))
        code, out = sdem('bian', 'custom', '--workspace', 'workspaces/pay', '--only', 'Term Deposit', '--person', 'jane.architect', cwd=self.tmp)
        self.assertEqual(code, 1); self.assertIn('approved connection', out)

    def test_aid_plans_from_a_workspace_kept_apart(self):  # WS-05
        self.assertEqual(sdem('new', '--workspace', 'ws', '--person', 'jane.architect', '--bian', EX / 'a2-service-domain.json', cwd=self.tmp)[0], 0)
        code, out = sdem('aid', 'project', '--workspace', 'ws', cwd=self.tmp)
        self.assertEqual(code, 2); self.assertIn('no business layer', out)
        shutil.copy(EX / 'a1-business.json', self.tmp / 'ws' / 'a1-business.json')
        code, out = sdem('aid', 'project', '--workspace', 'ws', cwd=self.tmp)
        self.assertEqual(code, 0, out); self.assertIn('ws/plans/PLAN-001', out)
        self.assertTrue((self.tmp / 'ws' / 'plans' / 'PLAN-001').exists())
        self.assertEqual(json.loads((self.tmp / 'ws' / 'a3-application.json').read_text())['instances'], [])   # nothing planned enters the real layers
        self.assertEqual(sdem('check', '--workspace', 'ws', cwd=self.tmp)[0], 0)
        code, out = sdem('aid', 'gaps', 'ws/plans/PLAN-001', '--workspace', 'ws', cwd=self.tmp)
        self.assertEqual(code, 0, out); self.assertIn('A2 service domains', out)
        self.assertIn('PLAN-002', sdem('aid', 'project', '--workspace', 'ws', cwd=self.tmp)[1])


if __name__ == '__main__':
    unittest.main()
