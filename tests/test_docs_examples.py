"""Examples printed in the user documents work as printed (two new-architect walkthroughs found ones that did not)."""
import json, re, shutil, tempfile, unittest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from forms import lf   # noqa: E402 — a layer's file in either form

from sdem import load, transform

ROOT = Path(__file__).resolve().parents[1]
import sys as _s2, pathlib as _pl2; _s2.path.insert(0, str(_pl2.Path(__file__).resolve().parent)); from needs import EXAMPLES  # noqa: E402 — SDEM's examples and sdem-bian's (R-D6)



def start(ws, **kw):
    """A workspace to load into — `sdem new` (WS-01); without a BIAN layer unless one is given."""
    import contextlib, io
    from sdem import new
    args = ['--workspace', str(ws), '--person', 'jane.architect'] + (['--bian', str(kw['bian'])] if kw.get('bian') else ['--no-bian'])
    with contextlib.redirect_stdout(io.StringIO()): assert new.main(args) == 0
    return ws

import sys as _s, pathlib as _pl; _s.path.insert(0, str(_pl.Path(__file__).resolve().parent)); from needs import bian as _needs_bian  # noqa: E402 — BX-15: tests that need sdem-bian

@_needs_bian
class DocumentedExamplesTests(unittest.TestCase):
    def setUp(self):   # 0.22 (BX-15): outside a workspace, as a command run alone — BIAN on where sdem-bian is installed (BX-12), whatever a test before opened
        from sdem import profile as _p; _p.deactivate()

    def test_the_starter_bian_layer_loads(self):  # docs/sdem-onboarding-workflow.md — "Your BIAN (A2) layer"
        doc = (ROOT / 'docs' / 'sdem-onboarding-workflow.md').read_text(encoding='utf-8')
        sec = doc[doc.index('A starter file with one service domain'):]
        starter = json.loads(re.search(r'```json\n(.*?)```', sec, re.S).group(1))
        tmp = Path(tempfile.mkdtemp())
        try:
            (tmp / 'a2-service-domain.json').write_text(json.dumps(starter), encoding='utf-8')
            transform.extract(EXAMPLES / 'designs' / 'confluence-folder-export', tmp / 'history', ocr='off')
            res = load.load(tmp / 'history', start(tmp / 'estate'), 'jane.architect', exclude=['HIS-A3-PAYMENT-ORDER'], a2=tmp / 'a2-service-domain.json')
            self.assertGreater(res['reconciliation']['loaded'], 0)
            self.assertTrue(lf(tmp / 'estate', 'bian').exists())
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_explain_gives_the_rule_in_words_and_its_source(self):  # promised by the user guide §8.2 and the glossary
        import subprocess, sys
        tmp = Path(tempfile.mkdtemp())
        try:
            est = tmp / 'est'; shutil.copytree(EXAMPLES / 'payment-initiation', est, ignore=shutil.ignore_patterns('graph'))
            shutil.copyfile(est / 'm1-mappings-given.json', est / 'mappings.json')
            run = lambda *a: subprocess.run([sys.executable, '-m', 'sdem', *a], cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(run('link', '--workspace', str(est), '--out', str(tmp / 'links')).returncode, 0)
            out = run('explain', 'P-RUN-013', '--proposals', str(tmp / 'links' / 'proposals.json')).stdout
            self.assertIn('rule says', out); self.assertIn('sources           [SAPG] https://', out)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == '__main__':
    unittest.main()
