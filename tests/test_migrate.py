"""`sdem migrate` — an estate moves to the current metamodel version only by recorded migrations, checked before writing."""
import json, shutil, tempfile, unittest
from pathlib import Path

from sdem import migrate as M
from sdem.metamodel import Metamodel

ROOT = Path(__file__).resolve().parents[1]
CUR = Metamodel.load().version


class MigrateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()); self.est = self.tmp / 'est'
        shutil.copytree(ROOT / 'examples' / 'payment-initiation', self.est, ignore=shutil.ignore_patterns('graph'))
        p = self.est / 'a3-application.json'; d = json.loads(p.read_text())
        d['metamodel_version'] = '0.3.0'
        self.inst = next(i for i in d['instances'] if i.get('attributes'))
        self.attr = next(iter(self.inst['attributes']))
        self.inst['attributes']['old_' + self.attr] = self.inst['attributes'].pop(self.attr)  # what an older metamodel called it
        p.write_text(json.dumps(d))
        self.rec = {'migrations': [{'from': '0.3.0', 'to': CUR, 'steps': [{'step': 'rename_attribute', 'from': 'old_' + self.attr, 'to': self.attr}]}]}

    def tearDown(self): shutil.rmtree(self.tmp, ignore_errors=True)

    def a3(self): return json.loads((self.est / 'a3-application.json').read_text())

    def test_chain(self):
        m = [{'from': '0.1', 'to': '0.2'}, {'from': '0.2', 'to': '0.3'}]
        self.assertEqual([x['to'] for x in M.chain('0.1', '0.3', m)], ['0.2', '0.3'])
        self.assertIsNone(M.chain('0.0', '0.3', m))
        self.assertEqual(M.chain('0.3', '0.3', m), [])

    def test_migrates_checks_and_records(self):
        res = M.migrate(self.est, 'jane.architect', migrations=self.rec, now='2026-10-29T00:00:00')
        d = self.a3(); i = next(x for x in d['instances'] if x['id'] == self.inst['id'])
        self.assertEqual(d['metamodel_version'], CUR)
        self.assertIn(self.attr, i['attributes']); self.assertNotIn('old_' + self.attr, i['attributes'])
        self.assertEqual(res['id'], 'MIG-001'); self.assertEqual(res['changes'], {'rename_attribute': 1})
        rec = json.loads((self.est / 'migrations' / 'MIG-001.json').read_text())
        self.assertEqual(rec['person'], 'jane.architect'); self.assertEqual(rec['files'][0]['from'], '0.3.0')
        self.assertEqual(M.migrate(self.est, 'jane.architect', migrations=self.rec)['note'][:7], 'already')

    def test_dry_run_writes_nothing(self):
        before = (self.est / 'a3-application.json').read_bytes()
        res = M.migrate(self.est, 'jane.architect', dry_run=True, migrations=self.rec)
        self.assertTrue(res['dry_run']); self.assertEqual((self.est / 'a3-application.json').read_bytes(), before)
        self.assertFalse((self.est / 'migrations').exists())

    def test_no_recorded_path_is_refused(self):
        with self.assertRaisesRegex(M.MigrateError, 'no migration path from metamodel 0.3.0'):
            M.migrate(self.est, 'jane.architect', migrations={'migrations': []})

    def test_a_migration_that_breaks_the_estate_writes_nothing(self):
        bad = {'migrations': [{'from': '0.3.0', 'to': CUR, 'steps': [{'step': 'rename_type', 'from': self.inst['type'], 'to': 'A3.NoSuchType'}]}]}
        before = (self.est / 'a3-application.json').read_bytes()
        with self.assertRaisesRegex(M.MigrateError, 'would not pass its checks'):
            M.migrate(self.est, 'jane.architect', migrations=bad)
        self.assertEqual((self.est / 'a3-application.json').read_bytes(), before)

    def test_a_person_decides(self):
        with self.assertRaisesRegex(ValueError, 'person'):
            M.migrate(self.est, 'copilot', migrations=self.rec)

    def test_the_mismatch_error_names_the_command(self):
        from sdem.graph import LevelGraph
        issues = LevelGraph(self.a3(), Metamodel.load()).validate()
        self.assertTrue(any('sdem migrate' in i for i in issues), issues[:3])

    def test_the_metamodel_record_is_well_formed(self):
        rec = json.loads((ROOT / 'metamodel' / 'migrations.json').read_text())
        self.assertEqual(rec['metamodel_version'], CUR)
        kinds = {'rename_type', 'rename_attribute', 'drop_attribute', 'set_attribute', 'rename_kind', 'rename_relationship'}
        for m in rec['migrations']:
            self.assertTrue({'from', 'to'} <= set(m)); self.assertTrue(all(s['step'] in kinds for s in m.get('steps', [])))
        if rec['migrations']:  # every older version reaches the current one
            for m in rec['migrations']: self.assertIsNotNone(M.chain(m['from'], CUR, rec['migrations']))


if __name__ == '__main__':
    unittest.main()
