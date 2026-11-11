"""`sdem document verify` (docs/design/sdem-workbench-ux-spec.md UX-D09…UX-D11): a narrative an agent writes from `sdem document --json`
is checked against the workspace — cited ids exist, stated links exist and are approved, named records are cited, inferred records
are said to be inferred, gaps are mentioned. The CLI itself never writes prose. Synthetic example workspace only."""
import json, os, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from sdem.document import verify, document   # noqa: E402

WS = ROOT / 'examples' / 'payment-initiation'

GOOD = """# Payments application architecture

Payments Hub [APP-PAY-HUB] is built from Instruction Capture [CMP-PAY-CAPTURE] [APP-PAY-HUB composition CMP-PAY-CAPTURE].

It runs on Managed Kubernetes — payments (production) [INF-K8S-PAY-PROD] [APP-PAY-HUB DEPLOYED_ON INF-K8S-PAY-PROD], approved as [PAY-108].

## Gaps and open items

Instruction Capture [CMP-PAY-CAPTURE] has no approved connection to another layer yet.
"""


def sdem(*args):
    env = {**os.environ, 'PYTHONPATH': str(ROOT) + os.pathsep + os.environ.get('PYTHONPATH', '')}
    r = subprocess.run([sys.executable, '-m', 'sdem', *map(str, args)], cwd=ROOT, capture_output=True, text=True, env=env)
    return r.returncode, r.stdout + r.stderr


def codes(r, level=None): return [f['code'] for f in r['findings'] if level in (None, f['level'])]


class VerifyTests(unittest.TestCase):
    def test_a_cited_narrative_passes(self):   # UX-D09
        r = verify(GOOD, WS)
        self.assertEqual((r['errors'], r['warnings']), (0, 0), r['findings']); self.assertEqual(r['cited'], 7)

    def test_invented_records_and_links_are_errors(self):   # UX-D09
        r = verify(GOOD + '\nIt calls the Fraud Engine [APP-FRAUD-ENGINE] [APP-PAY-HUB DEPLOYED_ON CMP-PAY-CAPTURE] through [PAY-999].\n', WS)
        self.assertEqual(sorted(codes(r, 'error')), ['unknown_id', 'unknown_id', 'unknown_link'])

    def test_only_approved_connections_are_facts(self):   # UX-D09
        ws = Path(tempfile.mkdtemp()); self.addCleanup(shutil.rmtree, ws, True)
        shutil.copytree(WS, ws / 'w'); ws = ws / 'w'
        reg = json.loads((ws / 'mappings.json').read_text())
        m = next(x for x in reg['mappings'] if x['mapping_id'] == 'PAY-108'); m['status'] = 'proposed'
        (ws / 'mappings.json').write_text(json.dumps(reg))
        self.assertIn('not_approved', codes(verify(GOOD, ws), 'error'))
        said = GOOD.replace('approved as [PAY-108]', 'proposed as [PAY-108]')
        self.assertNotIn('not_approved', codes(verify(said, ws)))   # stated as proposed: fine

    def test_named_but_not_cited_and_longest_name_first(self):   # UX-D10
        r = verify(GOOD + '\nExecution Gateway hands payments on.\n', WS)
        self.assertEqual(codes(r), ['uncited_name'])
        self.assertIn("'Execution Gateway'", r['findings'][0]['message'])   # not 'Execution' (a behaviour qualifier) inside it

    def test_inferred_records_said_to_be_inferred(self):   # UX-D10
        ws = Path(tempfile.mkdtemp()); self.addCleanup(shutil.rmtree, ws, True)
        shutil.copytree(WS, ws / 'w'); ws = ws / 'w'
        a3 = json.loads((ws / 'a3-application.json').read_text())
        rec = next(i for i in a3['instances'] if i['id'] == 'CMP-PAY-CAPTURE')
        rec.setdefault('attributes', {})['inferred'] = {'status': 'inferred', 'run': 'AID-001', 'rule': 'R3', 'confidence': 'low', 'reasoning': 'made up'}
        (ws / 'a3-application.json').write_text(json.dumps(a3))
        self.assertIn('unconfirmed_as_fact', codes(verify(GOOD, ws)))
        said = GOOD.replace('is built from Instruction Capture', 'is built from Instruction Capture, inferred and not yet confirmed,')
        self.assertEqual(codes(verify(said, ws), 'warning').count('unconfirmed_as_fact'), 1)   # the gaps paragraph still states it plainly

    def test_gaps_and_citations_required(self):   # UX-D10
        self.assertEqual(codes(verify('Payments are processed quickly.\n', WS), 'error'), ['no_citations'])
        self.assertIn('gaps_not_mentioned', codes(verify('Payments Hub [APP-PAY-HUB] is in-house.\n', WS)))
        self.assertTrue(document(WS, 'A3')['gaps']['no_connection'])

    def test_code_blocks_are_not_read(self):
        r = verify(GOOD + '\n```\n[NOT-AN-ID-123]\n```\n', WS)
        self.assertEqual(r['errors'], 0)

    def test_cli_exit_codes(self):   # UX-D11: read-only; exit 1 on an error
        d = Path(tempfile.mkdtemp()); self.addCleanup(shutil.rmtree, d, True)
        (d / 'good.md').write_text(GOOD); (d / 'bad.md').write_text(GOOD + '\n[APP-NOPE]\n')
        before = {p: p.read_bytes() for p in WS.glob('*.json')}
        code, out = sdem('document', 'verify', d / 'good.md', '--workspace', WS)
        self.assertEqual(code, 0, out); self.assertIn('0 error(s), 0 warning(s)', out)
        code, out = sdem('document', 'verify', d / 'bad.md', '--workspace', WS, '--json')
        self.assertEqual(code, 1); self.assertEqual(json.loads(out)['findings'][0]['code'], 'unknown_id')
        self.assertEqual(before, {p: p.read_bytes() for p in WS.glob('*.json')})
        code, out = sdem('document', '--workspace', WS, '--layer', 'A3')   # the structured document is unchanged: no prose
        self.assertEqual(code, 0); self.assertIn('### Payments Hub (APP-PAY-HUB)', out)


class SkillTests(unittest.TestCase):
    def test_the_skill_is_installed_for_every_agent(self):
        src = (ROOT / '.github' / 'skills' / 'sdem-design-narrative' / 'SKILL.md').read_text()
        for d in ('.claude', '.agents'):
            self.assertEqual((ROOT / d / 'skills' / 'sdem-design-narrative' / 'SKILL.md').read_text(), src)
        self.assertIn('sdem document verify', src); self.assertIn('never architecture data', src)
        self.assertIn('sdem-design-narrative', (ROOT / 'templates' / 'agents' / 'AGENTS.md').read_text())


if __name__ == '__main__':
    unittest.main()
