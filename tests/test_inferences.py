"""SDEM's record of inferred BIAN asset types and functional patterns (sdem/inferences.py; owner's decision DA2-03; spec BI-C08…BI-C11):
one traceable entry per domain BIAN does not publish values for; applied only when accepted; every change by a person, with a reason, in the history."""
import json, os, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from sdem import bian, inferences  # noqa: E402

RECORD = ROOT / 'bian' / 'inferences-14.0.0.json'


def sdem(*args, cwd=ROOT):
    env = {**os.environ, 'PYTHONPATH': str(ROOT) + os.pathsep + os.environ.get('PYTHONPATH', '')}   # run from any folder, installed or not (CI is not)
    r = subprocess.run([sys.executable, '-m', 'sdem', 'bian', *map(str, args)], cwd=cwd, capture_output=True, text=True, env=env)
    return r.returncode, r.stdout + r.stderr


class InferenceRecordTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()); (self.tmp / 'bian').mkdir()
        shutil.copy(RECORD, self.tmp / 'bian' / RECORD.name); self.rec = self.tmp / 'bian' / RECORD.name

    def tearDown(self): shutil.rmtree(self.tmp, ignore_errors=True)

    def entry(self, i): return next(e for e in json.loads(self.rec.read_text())['entries'] if e['id'] == i)

    def test_the_record_covers_every_domain_bian_does_not_publish_values_for(self):  # BI-C08
        rec = inferences.read(RECORD); domains = bian.read_pack(bian.base_file())
        underivable = {d['name'].lower() for d in domains if not bian.derive(d['control_record'])[0]}
        self.assertEqual({e['service_domain'].lower() for e in rec['entries']}, underivable)
        self.assertEqual(len(rec['entries']), 66)
        self.assertEqual(inferences.check(rec, {d['name'].lower() for d in domains}), [])
        for e in rec['entries']:   # every value states its source, reasoning and confidence
            for f in inferences.FIELDS:
                if e[f]: self.assertTrue(all(e[f][k] for k in ('value', 'confidence', 'source', 'reasoning')), e['id'])

    def test_only_accepted_entries_are_applied_and_traceable(self):  # BI-C09
        out = self.tmp / 'a2.json'
        code, text = sdem('import', '--base', '--all', '--inferences', self.rec, '-o', out)
        self.assertEqual(code, 0, text); self.assertIn('inferred: 48', text); self.assertIn('not known yet: 18', text)   # the owner accepted 48 (2026-10-30)
        sds = {i['name']: i['attributes'] for i in json.loads(out.read_text())['instances'] if i['type'] == 'A2.ServiceDomain'}
        self.assertEqual((sds['Term Deposit']['classification'], sds['Term Deposit']['inference_ref']), ('inferred', 'BI-INF-062'))
        self.assertEqual(sds['Interactive Help'], {k: v for k, v in sds['Interactive Help'].items() if k in ('source_id', 'conforms_to')} | {'classification': 'unknown'})  # proposed: not applied
        self.assertEqual(sdem('inference', 'accept', 'BI-INF-031', '--person', 'jane.architect', '--reason', 'checked', cwd=self.tmp)[0], 0)
        code, text = sdem('import', '--base', '--all', '--inferences', self.rec, '-o', out)
        self.assertIn('inferred: 49', text); self.assertIn('not known yet: 17', text)
        self.assertIn('BI-INF-031', (self.tmp / 'a2.report.md').read_text())
        code, text = sdem('import', '--base', '--all', '--inferences', self.rec, '--no-inferences', '-o', out)
        self.assertIn('not known yet: 66', text)

    def test_every_change_is_a_persons_with_a_reason_and_in_the_history(self):  # BI-C10, BI-C11
        code, out = sdem('inference', 'accept', 'BI-INF-031', '--person', 'sdem-agent', cwd=self.tmp)
        self.assertEqual(code, 2); self.assertIn('not a person', out)
        code, out = sdem('inference', 'challenge', 'BI-INF-062', '--person', 'jane.architect', cwd=self.tmp)
        self.assertEqual(code, 2); self.assertIn('--reason', out)
        code, out = sdem('inference', 'accept', 'BI-INF-062', '--person', 'jane.architect', cwd=self.tmp)
        self.assertEqual(code, 2); self.assertIn('already accepted', out)
        self.assertEqual(sdem('inference', 'challenge', 'BI-INF-062', '--person', 'raj.reviewer', '--reason', 'reads as Process', cwd=self.tmp)[0], 0)
        self.assertEqual(self.entry('BI-INF-062')['status'], 'challenged')     # challenged: no longer applied
        code, out = sdem('inference', 'change', 'BI-INF-062', '--pattern', 'Process', '--confidence', 'medium', '--source', 'BIAN portal',
                         '--person', 'raj.reviewer', '--reason', 'portal says Process', cwd=self.tmp)
        self.assertEqual(code, 0, out)
        e = self.entry('BI-INF-062')
        self.assertEqual((e['functional_pattern']['value'], e['status']), ('Process', 'proposed'))   # changed values need accepting again
        self.assertEqual([h['action'] for h in e['history']], ['proposed', 'accept', 'challenge', 'change'])
        self.assertEqual(e['history'][1]['by'], 'taumoeps')
        self.assertEqual(e['history'][-1]['before']['functional_pattern'], 'Fulfill')
        self.assertEqual(inferences.check(json.loads(self.rec.read_text())), [])
        code, out = sdem('inference', 'change', 'BI-INF-062', '--pattern', 'Juggle', '--source', 'x', '--person', 'raj.reviewer', '--reason', 'x', cwd=self.tmp)
        self.assertEqual(code, 2); self.assertIn('not a BIAN functional pattern', out)

    def test_a_hand_edit_is_caught(self):  # BI-C10
        rec = json.loads(self.rec.read_text())
        next(e for e in rec['entries'] if e['id'] == 'BI-INF-062')['functional_pattern']['value'] = 'Process'
        self.assertTrue(any('without a history entry' in x for x in inferences.check(rec)))

    def test_open_entries_get_values_through_change(self):  # BI-C11
        code, out = sdem('inference', 'accept', 'BI-INF-017', '--person', 'jane.architect', cwd=self.tmp)
        self.assertEqual(code, 2); self.assertIn('no values', out)
        code, out = sdem('inference', 'change', 'BI-INF-017', '--asset-type', 'Trading Credit Position', '--pattern', 'Analyse', '--source', 'our BIAN owner',
                         '--person', 'jane.architect', '--reason', 'Measurement reads as analysis', cwd=self.tmp)
        self.assertEqual(code, 0, out); self.assertEqual(self.entry('BI-INF-017')['status'], 'proposed')

    def test_list_and_show(self):
        code, out = sdem('inference', 'list', '--status', 'open')
        self.assertEqual(code, 0, out); self.assertIn('6 entries', out)
        code, out = sdem('inference', 'show', 'BI-INF-062')
        self.assertEqual(code, 0, out); self.assertIn('Term Deposit', out); self.assertIn('source:', out); self.assertIn('history:', out)


if __name__ == '__main__':
    unittest.main()
