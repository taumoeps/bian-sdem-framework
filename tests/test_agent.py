"""SDEM driven the way an agent drives it (docs/design/sdem-agent-cli-spec.md, AF-01…AF-06): the whole workflow — new, check, aid,
confirm, link, approve, build, trace, impact, dashboard — with --json only; every result is JSON with the sdem marker; failures
are JSON with a code and a hint; --dry-run writes nothing; --limit cuts lists; `sdem commands --json` lists every command."""
import hashlib, json, os, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
G = ROOT / 'examples' / 'payment-initiation' / 'graph'
A1 = [{'id': 'CAP-1', 'type': 'A1.BusinessCapability', 'version': '1', 'name': 'Payment Initiation', 'lifecycle_status': 'active'},
      {'id': 'PRC-1', 'type': 'A1.BusinessProcess', 'version': '1', 'name': 'Make a payment', 'lifecycle_status': 'active'},
      {'id': 'ACT-1', 'type': 'A1.BusinessActivity', 'version': '1', 'name': 'Initiate payment order', 'lifecycle_status': 'active',
       'attributes': {'sequence': 1}}]


def sdem(*args, cwd, ok=(0,)):
    env = {**os.environ, 'PYTHONPATH': str(ROOT) + os.pathsep + os.environ.get('PYTHONPATH', '')}   # installed or not (CI is not)
    r = subprocess.run([sys.executable, '-m', 'sdem', *map(str, args)], cwd=cwd, capture_output=True, text=True, env=env)
    try: data = json.loads(r.stdout)
    except ValueError: raise AssertionError(f'sdem {" ".join(map(str, args))}: stdout is not JSON (exit {r.returncode}):\n{r.stdout[:400]}\n{r.stderr[-400:]}')
    if r.returncode not in ok: raise AssertionError(f'sdem {" ".join(map(str, args))}: exit {r.returncode}: {json.dumps(data)[:600]}')
    return r.returncode, data


def tree_hash(d):
    h = hashlib.sha256()
    for p in sorted(Path(d).rglob('*')):
        if p.is_file(): h.update(str(p.relative_to(d)).encode()); h.update(p.read_bytes())
    return h.hexdigest()


class AgentTests(unittest.TestCase):
    def setUp(self): self.tmp = Path(tempfile.mkdtemp())
    def tearDown(self): shutil.rmtree(self.tmp, ignore_errors=True)

    def test_the_whole_workflow_with_json_only(self):  # AG-01, AG-03, AG-04
        t = self.tmp
        _, d = sdem('new', '--workspace', 'ws', '--person', 'jane.architect', '--json', cwd=t)
        self.assertEqual(d['sdem']['command'], 'new')
        a1 = json.loads((t / 'ws' / 'a1-business.json').read_text())
        a1['instances'] = A1; a1['relationships'] = [{'source': 'PRC-1', 'kind': 'composition', 'target': 'ACT-1'}]
        (t / 'ws' / 'a1-business.json').write_text(json.dumps(a1))
        self.assertTrue(sdem('check', '--workspace', 'ws', '--json', cwd=t)[1]['ok'])
        before = tree_hash(t / 'ws')
        _, d = sdem('aid', '--workspace', 'ws', '--person', 'jane.architect', '--json', '--dry-run', cwd=t)
        self.assertIn('SD-PAYMENT-ORDER-INITIATION', d['added']['A2']); self.assertEqual(tree_hash(t / 'ws'), before)   # its own dry run
        _, d = sdem('aid', '--workspace', 'ws', '--person', 'jane.architect', '--json', cwd=t)
        self.assertEqual(d['sdem'], {'version': d['sdem']['version'], 'command': 'aid'}); self.assertTrue(d['proposed_connections'])
        before = tree_hash(t / 'ws')
        _, d = sdem('aid', 'confirm', '--all', '--workspace', 'ws', '--person', 'jane.architect', '--json', '--dry-run', cwd=t)
        self.assertTrue(d['dry_run']); self.assertTrue(any('a2-service-domain.json' in w for w in d['would_write']))
        self.assertEqual(tree_hash(t / 'ws'), before)                                                       # the sandbox: nothing written
        _, d = sdem('aid', 'confirm', '--all', '--workspace', 'ws', '--person', 'jane.architect', '--json', cwd=t)
        self.assertGreater(d['count'], 10)
        _, d = sdem('link', '--workspace', 'ws', '--out', 'ws/links', '--json', cwd=t)
        self.assertEqual(d['count'], len(d['proposals'])); self.assertTrue(d['proposals'])
        self.assertLessEqual(d['proposals'][0]['confidence'], d['proposals'][-1]['confidence'])            # weakest first
        p = d['proposals'][0]
        code, d = sdem('approve', p['id'], '--proposals', 'ws/links/proposals.json', '--workspace', 'ws', '--reviewer', 'jane.architect',
                       '--evidence', 'process_model:PM-1', '--json', cwd=t, ok=(0, 1))
        self.assertIn('sdem', d)
        _, d = sdem('build', '--workspace', 'ws', '--out', 'ws/graph', '--json', cwd=t)
        self.assertEqual(d['result'], 'accepted'); self.assertIn('next', d)
        _, d = sdem('trace', 'A1', '--direction', 'down', '--graph', 'ws/graph', '--json', cwd=t)
        self.assertIsInstance(d, list)                                                                     # a layer trace: one result per layer
        _, d = sdem('dashboard', '--workspace', 'ws', '--json', cwd=t)
        self.assertLess(len(json.dumps(d)), 40000); self.assertIn('more', d)                                # AG-02: a summary by default

    def test_failures_are_json_with_a_code_and_a_hint(self):  # AG-05
        cases = [(('trace', 'NOPE', '--graph', G), 1, 'not_found', 'sdem query'),
                 (('check', '--workspace', self.tmp / 'none'), 2, 'not_found', 'sdem new'),
                 (('trace', 'A4', '--graph', G, '--direction', 'sideways'), 2, 'usage', 'sdem trace --help'),
                 (('new', '--workspace', self.tmp / 'x', '--person', 'sdem-agent'), 2, 'needs_person', 'person'),
                 (('trace', 'A4', '--graph', G, '--limit', 'many'), 2, 'usage', None)]
        for args, code, kind, hint in cases:
            with self.subTest(args=args[:2]):
                got, d = sdem(*args, '--json', cwd=self.tmp, ok=(code,))
                self.assertEqual((d['error']['code'], d['error']['exit']), (kind, code)); self.assertTrue(d['error']['message'])
                if hint: self.assertIn(hint, d['error']['hint'])

    def test_limit_and_size(self):  # AG-02
        _, d = sdem('trace', 'INF-K8S-PAY-PROD', '--graph', G, '--json', '--limit', '1', cwd=self.tmp)
        self.assertTrue(d['truncated']); self.assertTrue(all(len(v) <= 1 for v in [d.get('down', {}).get('children', [])]))
        _, d = sdem('home', '-o', self.tmp / 'h', '--json', cwd=ROOT)
        self.assertLess(len(json.dumps(d)), 40000); self.assertIn('version', d['metamodel'])

    def test_a_command_with_no_json_of_its_own_is_wrapped(self):  # AG-03
        _, d = sdem('transform', 'rules', '-o', 'rules.csv', '--json', cwd=self.tmp)
        self.assertEqual((d['sdem']['command'], d['ok'], d['exit']), ('transform rules', True, 0)); self.assertTrue(d['output'])
        before = sorted(p.name for p in self.tmp.iterdir())
        _, d = sdem('transform', 'rules', '-o', 'other.csv', '--json', '--dry-run', cwd=self.tmp)   # AG-04: the sandbox
        self.assertEqual(d['would_write'], ['write: other.csv']); self.assertEqual(sorted(p.name for p in self.tmp.iterdir()), before)

    def test_every_command_is_listed_as_data(self):  # AG-06
        _, d = sdem('commands', '--json', cwd=self.tmp)
        cmds = d['commands']
        for c in ('new', 'aid', 'aid confirm', 'link', 'approve', 'build', 'trace', 'bian inference list'):
            self.assertIn(c, cmds)
        self.assertEqual(cmds['trace']['json'], 'native'); self.assertIn('--direction', [o['name'] for o in cmds['trace']['options']])
        self.assertEqual(cmds['new']['dry_run'], 'native')
        self.assertEqual(sorted(d['exit_codes']), ['0', '1', '2', '3'])
        wrapped = sorted(n for n, c in cmds.items() if c.get('json') == 'wrapped')   # only maintainers' tools lack JSON of their own
        self.assertTrue(all(n.startswith(('model', 'transform rules', 'bian pack')) for n in wrapped), wrapped)


if __name__ == '__main__':
    unittest.main()
