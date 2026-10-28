"""Examples printed in the user documents work as printed (two new-architect walkthroughs found ones that did not)."""
import json, re, shutil, tempfile, unittest
from pathlib import Path

from sdem import load, transform

ROOT = Path(__file__).resolve().parents[1]


class DocumentedExamplesTests(unittest.TestCase):
    def test_the_starter_bian_layer_loads(self):  # docs/sdem-onboarding-workflow.md — "Your BIAN (A2) layer"
        doc = (ROOT / 'docs' / 'sdem-onboarding-workflow.md').read_text(encoding='utf-8')
        sec = doc[doc.index('A starter file with one service domain'):]
        starter = json.loads(re.search(r'```json\n(.*?)```', sec, re.S).group(1))
        tmp = Path(tempfile.mkdtemp())
        try:
            (tmp / 'a2-service-domain.json').write_text(json.dumps(starter), encoding='utf-8')
            transform.extract(ROOT / 'examples' / 'designs' / 'confluence-folder-export', tmp / 'history', ocr='off')
            res = load.load(tmp / 'history', tmp / 'estate', 'jane.architect', exclude=['HIS-A3-PAYMENT-ORDER'], a2=tmp / 'a2-service-domain.json')
            self.assertGreater(res['reconciliation']['loaded'], 0)
            self.assertTrue((tmp / 'estate' / 'a2-service-domain.json').exists())
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_explain_gives_the_rule_in_words_and_its_source(self):  # promised by the user guide §8.2 and the glossary
        import subprocess, sys
        tmp = Path(tempfile.mkdtemp())
        try:
            est = tmp / 'est'; shutil.copytree(ROOT / 'examples' / 'payment-initiation', est, ignore=shutil.ignore_patterns('graph'))
            shutil.copyfile(est / 'm1-mappings-given.json', est / 'mappings.json')
            run = lambda *a: subprocess.run([sys.executable, '-m', 'sdem', *a], cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(run('link', '--estate', str(est), '--out', str(tmp / 'links')).returncode, 0)
            out = run('explain', 'P-RUN-013', '--proposals', str(tmp / 'links' / 'proposals.json')).stdout
            self.assertIn('rule says', out); self.assertIn('sources           [SAPG] https://', out)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == '__main__':
    unittest.main()
