"""SDEM driven the way an agent drives it (docs/design/sdem-agent-cli-spec.md, AF-01…AF-08): the whole workflow — new, check, aid,
confirm, link, approve, build, trace, dashboard — with --json only, each step using what the one before returned; every result is a
JSON object with the sdem marker; failures are JSON with a code and a hint; --dry-run writes nothing; --limit cuts lists; edits made
outside sdem are noticed; `sdem commands --json` lists every command."""
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

    def test_the_whole_workflow_with_json_only(self):  # AF-01, AF-03, AF-04
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
        p = next(x for x in d['proposals'] if x['relationship'] == 'DEPLOYED_AS')   # its evidence kind is known: a deployment design
        self.assertTrue(p['mapping_id'])                                                                    # the id approve needs
        reg = json.loads((t / 'ws' / 'mappings.json').read_text())
        _, d = sdem('approve', p['mapping_id'], '--proposals', 'ws/links/proposals.json', '--workspace', 'ws', '--reviewer', 'jane.architect',
                    '--evidence', 'deployment_design:DD-1', '--json', cwd=t)
        self.assertEqual(d['sdem']['command'], 'approve'); self.assertEqual(d['count'], len(d['items']))
        self.assertEqual(len(json.loads((t / 'ws' / 'mappings.json').read_text())['mappings']), len(reg['mappings']) + 1)   # the registry changed
        _, d = sdem('build', '--workspace', 'ws', '--out', 'ws/graph', '--json', cwd=t)
        self.assertEqual(d['result'], 'accepted'); self.assertIn('next', d)
        _, d = sdem('trace', 'A1', '--direction', 'down', '--graph', 'ws/graph', '--json', cwd=t)
        self.assertEqual((d['sdem']['command'], d['count']), ('trace', len(d['items'])))                     # AF-08: a list result is an object
        _, d = sdem('dashboard', '--workspace', 'ws', '--json', cwd=t)
        self.assertLess(len(json.dumps(d)), 40000); self.assertIn('more', d)                                # AF-02: a summary by default

    def test_failures_are_json_with_a_code_and_a_hint(self):  # AF-05
        cases = [(('trace', 'NOPE', '--graph', G), 1, 'not_found', 'sdem query'),
                 (('check', '--workspace', self.tmp / 'none'), 2, 'not_found', 'sdem new'),
                 (('trace', 'A4', '--graph', G, '--direction', 'sideways'), 2, 'usage', 'sdem trace --help'),
                 (('new', '--workspace', self.tmp / 'x', '--person', 'sdem-agent'), 2, 'needs_person', 'person'),
                 (('trace', 'A4', '--graph', G, '--limit', 'many'), 2, 'usage', None),
                 (('frobnicate',), 2, 'usage', 'sdem commands --json'),
                 (('validate', ROOT / 'pyproject.toml'), 2, 'invalid_input', 'fix the file'),
                 (('review', self.tmp / 'nope.json'), 2, 'not_found', None)]
        for args, code, kind, hint in cases:
            with self.subTest(args=args[:2]):
                got, d = sdem(*args, '--json', cwd=self.tmp, ok=(code,))
                self.assertEqual((d['error']['code'], d['error']['exit']), (kind, code)); self.assertTrue(d['error']['message'])
                self.assertTrue(d['error']['hint'])                                                  # every error has a next step
                if hint: self.assertIn(hint, d['error']['hint'])

    def test_an_edit_made_outside_sdem_is_noticed(self):  # AF-07
        t = self.tmp
        sdem('new', '--workspace', 'ws', '--person', 'jane.architect', '--json', cwd=t)
        _, d = sdem('check', '--workspace', 'ws', '--json', cwd=t)
        self.assertEqual(d['unrecorded_edits'], [])
        a1 = json.loads((t / 'ws' / 'a1-business.json').read_text()); a1['instances'] = A1[:1]
        (t / 'ws' / 'a1-business.json').write_text(json.dumps(a1))                                          # an edit not made through sdem
        _, d = sdem('check', '--workspace', 'ws', '--json', cwd=t)
        self.assertTrue(d['ok']); self.assertEqual([e['file'] for e in d['unrecorded_edits']], ['a1-business.json'])   # noticed, not failed
        code, d = sdem('check', '--workspace', 'ws', '--require-recorded', '--json', cwd=t, ok=(1,))
        self.assertFalse(d['ok'])                                                                          # CI: fails
        code, d = sdem('change', 'adopt', '--workspace', 'ws', '--layer', 'A1', '--person', 'sdem-a1-business', '--reason', 'x', '--json', cwd=t, ok=(1, 2))
        self.assertEqual(d['error']['code'], 'needs_person')                                               # an agent cannot accept it
        _, d = sdem('change', 'adopt', '--workspace', 'ws', '--layer', 'A1', '--person', 'jane.architect', '--reason', 'wrote the business layer', '--json', cwd=t)
        self.assertEqual(d['accepted'], 'a1-business.json')
        self.assertTrue(sdem('check', '--workspace', 'ws', '--require-recorded', '--json', cwd=t)[1]['ok'])

    def test_limit_and_size(self):  # AF-02
        _, d = sdem('trace', 'INF-K8S-PAY-PROD', '--graph', G, '--json', '--limit', '1', cwd=self.tmp)
        self.assertTrue(d['truncated']); self.assertTrue(all(len(v) <= 1 for v in [d.get('down', {}).get('children', [])]))
        _, d = sdem('home', '-o', self.tmp / 'h', '--json', cwd=ROOT)
        self.assertLess(len(json.dumps(d)), 40000); self.assertIn('version', d['metamodel'])

    def test_a_command_with_no_json_of_its_own_is_wrapped(self):  # AF-03
        _, d = sdem('transform', 'rules', '-o', 'rules.csv', '--json', cwd=self.tmp)
        self.assertEqual((d['sdem']['command'], d['ok'], d['exit']), ('transform rules', True, 0)); self.assertTrue(d['output'])
        before = sorted(p.name for p in self.tmp.iterdir())
        _, d = sdem('transform', 'rules', '-o', 'other.csv', '--json', '--dry-run', cwd=self.tmp)   # AF-04: the sandbox
        self.assertEqual(d['would_write'], ['write: other.csv']); self.assertEqual(sorted(p.name for p in self.tmp.iterdir()), before)

    def test_agents_install_one_source_for_every_platform(self):  # AF-09
        t = self.tmp
        _, d = sdem('agents', 'install', '--platform', 'claude', 'codex', '--json', cwd=t)
        self.assertIn('AGENTS.md', d['written']); self.assertIn('CLAUDE.md', d['written']); self.assertNotIn('copilot', d)
        self.assertEqual((t / 'CLAUDE.md').read_text().splitlines()[0], '@AGENTS.md')                       # a pointer, not a copy
        self.assertEqual((t / '.claude/skills/sdem-records/SKILL.md').read_text(), (t / '.agents/skills/sdem-records/SKILL.md').read_text())
        self.assertIn('/blob/v', (t / 'AGENTS.md').read_text())                                              # links pinned to this version
        (t / '.gemini').mkdir(); (t / '.gemini' / 'settings.json').write_text('{"theme": "mine"}')
        _, d = sdem('agents', 'install', '--json', cwd=t)
        self.assertIn('.gemini/settings.json', d['kept']); self.assertTrue(d['notes'])                      # the team's own settings are kept
        self.assertEqual(json.loads((t / '.gemini' / 'settings.json').read_text()), {'theme': 'mine'})
        self.assertTrue((t / '.github' / 'copilot-instructions.md').exists())

    def test_every_command_is_listed_as_data(self):  # AF-06
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
