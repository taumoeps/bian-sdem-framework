"""Regressions for the CLI defects found by the core-agent validation (docs/evidence/agent-core-validation.md, findings 3–13)."""
import json, os, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV = {**os.environ, 'PYTHONPATH': str(ROOT) + os.pathsep + os.environ.get('PYTHONPATH', '')}


def sdem(*args, cwd):
    return subprocess.run([sys.executable, '-m', 'sdem', *map(str, args)], cwd=cwd, capture_output=True, text=True, env=ENV)


class AgentCliFixesTests(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        shutil.copytree(ROOT / 'examples' / 'payment-initiation', self.d / 'ws', ignore=shutil.ignore_patterns('graph', 'migrations'))

    def tearDown(self): shutil.rmtree(self.d, ignore_errors=True)

    def test_a_closed_pipe_gives_no_traceback(self):                                     # finding 3
        p = subprocess.Popen([sys.executable, '-m', 'sdem', 'commands', '--json'], cwd=self.d, env=ENV, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        p.stdout.read(10); p.stdout.close(); err = p.stderr.read().decode(); p.stderr.close(); p.wait()
        self.assertNotIn('Traceback', err)

    def test_help_names_the_options_every_command_takes(self):                          # finding 4
        out = sdem('change', 'propose', '--help', cwd=self.d).stdout
        for opt in ('--json', '--dry-run', '--limit'): self.assertIn(opt, out.split('usage:')[-1].split('\n\n')[-1])

    def test_a_native_dry_run_is_marked(self):                                          # finding 5
        reg = self.d / 'ws' / 'mappings.json'; data = json.loads(reg.read_text(encoding='utf-8'))
        data['mappings'] = [m for m in data['mappings'] if m['mapping_id'] != 'PAY-106']   # SD-PI REALIZED_BY APP-PAY-HUB: proposed again
        reg.write_text(json.dumps(data, indent=2))
        links = json.loads(sdem('link', '--workspace', 'ws', '--out', 'ws/links', '--json', cwd=self.d).stdout)
        pid = next(x['mapping_id'] for x in links['proposals'] if (x['source'], x['target']) == ('SD-PI', 'APP-PAY-HUB'))
        r = sdem('approve', pid, '--proposals', 'ws/links/proposals.json', '--workspace', 'ws', '--reviewer', 'jane.architect',
                 '--evidence', 'application_architecture_document:X', '--dry-run', '--json', cwd=self.d)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertTrue(json.loads(r.stdout).get('dry_run'), r.stdout[:300])
        self.assertFalse(any(m['source']['id'] == 'SD-PI' and m['target']['id'] == 'APP-PAY-HUB' for m in json.loads(reg.read_text(encoding='utf-8'))['mappings']))

    def test_a_change_set_preview_reports_the_changed_fingerprint(self):                 # finding 6
        rec = next(i for i in json.loads((self.d / 'ws' / 'a3-application.json').read_text(encoding='utf-8'))['instances'] if i['id'] == 'APP-PAY-HUB')
        rec['description'] = 'changed'
        (self.d / 'cs.json').write_text(json.dumps({'layer': 'A3', 'reason': 'test', 'changes': [{'op': 'update', 'record': rec}]}))
        r = sdem('change', 'propose', 'cs.json', '--workspace', 'ws', '--agent', 'sdem-a3-application', '--person', 'jane.architect', '--dry-run', '--json', cwd=self.d)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        ds = json.loads(r.stdout)['change_set']['dataset']
        self.assertNotEqual(ds['before_sha256'], ds['after_sha256'])

    def test_events_list_is_the_list(self):                                             # finding 7
        r = sdem('events', 'list', '--workspace', 'ws', '--json', cwd=self.d)
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_types_matches_the_check(self):                                             # findings 9–11
        from sdem.conformance import LIFECYCLE
        a1 = sdem('types', 'A1', cwd=self.d).stdout
        self.assertIn(' | '.join(LIFECYCLE), a1)
        for line in a1.splitlines():
            if line.strip().startswith('links:'):
                items = line.split('links:', 1)[1].split(';')
                self.assertEqual(len(items), len(set(i.strip() for i in items)), line)
        self.assertIn('DEPRECATED', sdem('types', 'A3.ApplicationComponent', cwd=self.d).stdout)

    def test_limit_keeps_the_shape(self):                                                # found by the agents, run 2
        r = sdem('bian', 'search', 'payment', '--json', '--limit', '2', cwd=self.d)
        d = json.loads(r.stdout)
        self.assertIsInstance(d['results'][0], dict); self.assertLessEqual(len(d['results']), 2); self.assertIn('truncated', d)

    def test_a_refusal_says_why_in_json(self):                                           # found by the agents, run 2
        from sdem.agent import error_json
        e = error_json(1, 'ERROR: the registry would not pass its checks — nothing was written:\n  mapping #1: requires bian_release\n  → add --bian-release <release>', 'approve')['error']
        self.assertEqual(e['details'], ['mapping #1: requires bian_release']); self.assertEqual(e['hint'], 'add --bian-release <release>')

    def test_aid_help_shows_the_main_form(self):                                        # finding 12
        self.assertIn('sdem aid --workspace', sdem('aid', '--help', cwd=self.d).stdout)


class OwnerDecisionTests(unittest.TestCase):   # O6, O7 (owner's decisions 2026-11-06)
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        shutil.copytree(ROOT / 'examples' / 'payment-initiation', self.d / 'ws', ignore=shutil.ignore_patterns('graph', 'migrations'))
        reg = self.d / 'ws' / 'mappings.json'; data = json.loads(reg.read_text(encoding='utf-8'))
        data['mappings'] = [m for m in data['mappings'] if m['mapping_id'] != 'PAY-106']
        reg.write_text(json.dumps(data, indent=2), encoding='utf-8')

    def tearDown(self): shutil.rmtree(self.d, ignore_errors=True)

    def test_the_dashboard_and_link_give_a_proposal_the_same_id(self):                 # O6
        sys.path.insert(0, str(ROOT))
        from sdem.dashboard import collect
        dash = {(r['source'], r['rel'], r['target']): r['id'] for r in collect(self.d / 'ws')['review']['rows']}
        links = json.loads(sdem('link', '--workspace', 'ws', '--out', 'ws/links', '--json', cwd=self.d).stdout)['proposals']
        self.assertTrue(links)
        for p in links: self.assertEqual(dash.get((p['source'], p['relationship'], p['target'])), p['mapping_id'])

    def test_search_says_when_no_domain_has_that_name(self):                            # O7
        named = json.loads(sdem('bian', 'search', 'payment', 'execution', '--json', cwd=self.d).stdout)
        self.assertIn('no_domain_named', named)
        exact = json.loads(sdem('bian', 'search', 'party', 'authentication', '--json', cwd=self.d).stdout)
        self.assertNotIn('no_domain_named', exact)


if __name__ == '__main__':
    unittest.main()
