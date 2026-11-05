"""AG-V11 (owner's decision 2026-11-06): a change of name or description only is documentation — recorded, no structural impact,
no impact validation, blocks nothing. AG-V08/RR-G02: a further change to a record an open event changed gets its own event, and the
open event cannot be accepted until re-analysed."""
import json, os, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV = {**os.environ, 'PYTHONPATH': str(ROOT) + os.pathsep + os.environ.get('PYTHONPATH', '')}
P = ('--person', 'jane.architect')


def sdem(*args, cwd):
    r = subprocess.run([sys.executable, '-m', 'sdem', *map(str, args)], cwd=cwd, capture_output=True, text=True, env=ENV)
    return r.returncode, r.stdout + r.stderr


class DocumentationChangeTests(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        shutil.copytree(ROOT / 'examples' / 'payment-initiation', self.d / 'ws', ignore=shutil.ignore_patterns('graph', 'migrations'))

    def tearDown(self): shutil.rmtree(self.d, ignore_errors=True)

    def change(self, fname, layer, rid, **fields):
        f = {'A3': 'a3-application.json', 'A4': 'a4-technology.json'}[layer]
        rec = dict(next(i for i in json.loads((self.d / 'ws' / f).read_text(encoding='utf-8'))['instances'] if i['id'] == rid)); rec.update(fields)
        (self.d / fname).write_text(json.dumps({'layer': layer, 'reason': 'test', 'changes': [{'op': 'update', 'record': rec}]}), encoding='utf-8')
        agent = {'A3': 'sdem-a3-application', 'A4': 'sdem-a4-technology'}[layer]
        return sdem('change', 'propose', fname, '--workspace', 'ws', '--agent', agent, *P, cwd=self.d)

    def event(self, eid): return json.loads((self.d / 'ws' / 'coordination' / 'events' / f'{eid}.json').read_text(encoding='utf-8'))

    def test_a_description_change_is_documentation_and_blocks_nothing(self):
        code, out = self.change('a.json', 'A3', 'APP-PAY-HUB', description='new words')
        self.assertEqual(code, 0, out); self.assertIn('documentation only', out)
        ev = self.event('CE-001')
        self.assertTrue(ev['impact'].get('documentation_only')); self.assertEqual(ev['impact']['records'], [])
        self.assertIn('no change events open', sdem('events', '--workspace', 'ws', '--open', cwd=self.d)[1])
        code, out = self.change('b.json', 'A4', 'INF-K8S-PAY-PROD', name='Kubernetes — payments')   # was refused (AG-V08) after a description edit
        self.assertEqual(code, 0, out)
        self.assertEqual(sdem('check', '--workspace', 'ws', '--require-recorded', cwd=self.d)[0], 0)

    def test_an_explicit_modify_kind_is_no_different(self):                             # found by the agents, run 2
        rec = dict(next(i for i in json.loads((self.d / 'ws' / 'a3-application.json').read_text(encoding='utf-8'))['instances'] if i['id'] == 'APP-PAY-HUB'))
        rec['description'] = 'new words'
        (self.d / 'k.json').write_text(json.dumps({'layer': 'A3', 'reason': 't', 'changes': [{'op': 'update', 'kind': 'modify', 'record': rec}]}), encoding='utf-8')
        code, out = sdem('change', 'propose', 'k.json', '--workspace', 'ws', '--agent', 'sdem-a3-application', *P, cwd=self.d)
        self.assertEqual(code, 0, out); self.assertIn('documentation only', out)
        code, out = sdem('events', 'validate', 'CE-001', '--workspace', 'ws', '--agent', 'sdem-orchestrator', *P, cwd=self.d)
        self.assertNotEqual(code, 0); self.assertIn('AG-V11', out)                         # nothing to validate

    def test_any_other_field_is_an_ordinary_change(self):
        code, out = self.change('c.json', 'A3', 'APP-PAY-HUB', description='new words', lifecycle_status='planned')
        self.assertEqual(code, 0, out); self.assertNotIn('documentation only', out)
        self.assertFalse(self.event('CE-001')['impact'].get('documentation_only'))
        self.assertIn('CE-001', sdem('events', '--workspace', 'ws', '--open', cwd=self.d)[1])

    def test_a_further_change_to_the_changed_record_stales_the_open_event(self):       # AG-V08 / RR-G02, as intended
        self.assertEqual(self.change('c.json', 'A3', 'APP-PAY-HUB', lifecycle_status='planned')[0], 0)
        self.assertEqual(sdem('events', 'validate', 'CE-001', '--workspace', 'ws', '--agent', 'sdem-orchestrator', *P, cwd=self.d)[0], 0)
        v = json.loads((self.d / 'ws' / 'coordination' / 'validations' / 'IV-001.json').read_text(encoding='utf-8'))
        for l, agent in (('A1', 'sdem-a1-business'), ('A2', 'sdem-a2-bian'), ('A3', 'sdem-a3-application'), ('A4', 'sdem-a4-technology')):
            how = ['--status', 'impact_confirmed'] if v['layers'][l]['calculated']['classification'] != 'no_impact' else ['--status', 'no_impact_confirmed', '--uncertainty', 'off the changed path']
            code, out = sdem('events', 'assess', 'CE-001', '--layer', l, *how, '--evidence', f'design_review:{l}', '--reasoning', 'checked', '--workspace', 'ws', '--agent', agent, *P, cwd=self.d)
            self.assertEqual(code, 0, out)
        code, out = self.change('d.json', 'A3', 'APP-PAY-HUB', lifecycle_status='active')
        self.assertEqual(code, 0, out)                                                   # its own event: CE-002
        code, out = sdem('events', 'accept', 'CE-001', '--workspace', 'ws', *P, '--reason', 'x', cwd=self.d)
        self.assertNotEqual(code, 0); self.assertIn('RR-G02', out)


if __name__ == '__main__':
    unittest.main()
