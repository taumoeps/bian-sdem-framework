"""`sdem bian` — the BIAN (A2) layer from BIAN's public Semantic APIs (docs/design/sdem-bian-import-spec.md, BI-*).

Run against a made-up release in BIAN's shape (tests/fixtures/bian-release-sample — no BIAN text). The reader was also
checked against all 1,241 files of BIAN releases 10.0–14.0 (scripts/bian_import_check.py; extracted facts identical
to PyYAML's), which are not kept in this repository."""
import json, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

from sdem import bian

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / 'tests' / 'fixtures' / 'bian-release-sample'
BAD = ROOT / 'tests' / 'fixtures' / 'bian-release-bad'


def sdem(*args, cwd=ROOT):
    r = subprocess.run([sys.executable, '-m', 'sdem', 'bian', *map(str, args)], cwd=cwd, capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


class BianImportTests(unittest.TestCase):
    def setUp(self): self.tmp = Path(tempfile.mkdtemp())
    def tearDown(self): shutil.rmtree(self.tmp, ignore_errors=True)

    def imp(self, *extra, names=('Sample Order Initiation',)):
        out = self.tmp / 'a2.json'
        code, text = sdem('import', SAMPLE, '-o', out, '--only', *names, *extra)
        return code, text, out

    # ---- reading (BI-C01, C04, C05)
    def test_list_shows_the_release_and_writes_nothing(self):  # BI-C01
        before = set(SAMPLE.iterdir())
        code, out = sdem('list', SAMPLE)
        self.assertEqual(code, 0, out); self.assertIn('5 service domains in BIAN release 99.0.0', out)
        self.assertIn('Sample Order Initiation', out); self.assertEqual(set(SAMPLE.iterdir()), before)

    def test_reads_bians_yaml_forms(self):  # BI-C05: quoted and unquoted response codes, complex keys, keys with a colon
        d = bian.read_domain(SAMPLE / 'SamplePartyDirectory.yaml')
        self.assertEqual(d['name'], 'Sample Party Directory'); self.assertEqual(d['release'], '99.0.0')
        self.assertEqual(len(d['operations']), 3)
        self.assertTrue(d['operations'][0]['path'].endswith('/Written/As/A/Complex/Key'))
        self.assertEqual(d['operations'][0]['outputs'], ['PartyReference', 'PartyName', 'rwc:0000-made-up-key'])  # unquoted 200, colon key
        o = bian.read_domain(SAMPLE / 'SampleOrderInitiation.yaml')['operations'][0]
        self.assertEqual((o['method'], o['operation_id'], o['inputs']), ('POST', 'Initiate', ['OrderReference', 'Amount', 'Currency', 'PayerReference']))

    def test_refuses_what_it_does_not_read(self):  # BI-C04, BI-C05
        for f, why in (('OldSwagger.json', 'release 10.0.0 or later'), ('Anchors.yaml', 'YAML form SDEM does not read'), ('Tabs.yaml', 'tab indentation')):
            with self.assertRaisesRegex(bian.BianError, why): bian.read_domain(BAD / f)
        code, out = sdem('list', BAD)
        self.assertEqual(code, 2); self.assertIn('no file could be read', out)

    def test_no_network(self):  # BI-C03
        src = (ROOT / 'sdem' / 'bian.py').read_text(encoding='utf-8')
        for word in ('urllib.request', 'http.client', 'socket', 'requests'):
            self.assertNotIn(f'import {word}', src)

    # ---- choosing (BI-C06)
    def test_must_choose_and_misses_suggest_names(self):
        code, out = sdem('import', SAMPLE, '-o', self.tmp / 'x.json')
        self.assertEqual(code, 2); self.assertIn('--only', out); self.assertIn('sdem bian list', out)
        code, out = sdem('import', SAMPLE, '-o', self.tmp / 'x.json', '--only', 'Sample Order Initiaton')
        self.assertEqual(code, 2); self.assertIn("did you mean Sample Order Initiation", out)
        self.assertFalse((self.tmp / 'x.json').exists())

    def test_choose_by_file_of_names(self):
        names = self.tmp / 'names.txt'; names.write_text('# my domains\nSample Order Initiation\nsamplepartydirectory\n', encoding='utf-8')
        code, out = sdem('import', SAMPLE, '-o', self.tmp / 'a2.json', '--from', names)
        self.assertEqual(code, 0, out)
        sds = [i['name'] for i in json.loads((self.tmp / 'a2.json').read_text())['instances'] if i['type'] == 'A2.ServiceDomain']
        self.assertEqual(sorted(sds), ['Sample Order Initiation', 'Sample Party Directory'])

    # ---- what is written (BI-W01…W07)
    def test_writes_the_a2_layer_with_its_links(self):  # BI-W01
        code, out, f = self.imp()
        self.assertEqual(code, 0, out)
        d = json.loads(f.read_text()); by = {i['id']: i for i in d['instances']}
        sd = by['SD-SAMPLE-ORDER-INITIATION']
        self.assertEqual((sd['canonical_id'], sd['version']), ('BIAN-SAMPLE-ORDER-INITIATION', '99.0.0'))
        so = by['SO-SAMPLE-ORDER-INITIATION-INITIATE']['attributes']
        self.assertEqual((so['action_term'], so['http_method']), ('Initiate', 'POST'))
        self.assertEqual(so['input_attributes'], ['OrderReference', 'Amount', 'Currency', 'PayerReference'])
        self.assertEqual(by['CR-SAMPLE-ORDER-INITIATION']['attributes']['attributes'], ['OrderReference', 'Amount', 'Currency', 'PayerReference'])
        q = by['SO-SAMPLE-ORDER-INITIATION-EVALUATE-CHECK']['attributes']
        self.assertEqual(q['behavior_qualifier'], 'BQ-SAMPLE-ORDER-INITIATION-CHECK')
        links = {(r['source'], r['kind'], r['target']) for r in d['relationships']}
        for l in (('SD-SAMPLE-ORDER-INITIATION', 'aggregation', 'CR-SAMPLE-ORDER-INITIATION'),
                  ('SD-SAMPLE-ORDER-INITIATION', 'composition', 'SG-SAMPLE-ORDER-INITIATION-SAMPLE-ORDER-INITIATION-TRANSACTION'),
                  ('SG-SAMPLE-ORDER-INITIATION-SAMPLE-ORDER-INITIATION-TRANSACTION', 'composition', 'SO-SAMPLE-ORDER-INITIATION-INITIATE'),
                  ('SO-SAMPLE-ORDER-INITIATION-INITIATE', 'access', 'CR-SAMPLE-ORDER-INITIATION'),
                  ('CR-SAMPLE-ORDER-INITIATION', 'composition', 'BQ-SAMPLE-ORDER-INITIATION-CHECK'),
                  ('SO-SAMPLE-ORDER-INITIATION-EVALUATE-CHECK', 'association', 'BQ-SAMPLE-ORDER-INITIATION-CHECK')):
            self.assertIn(l, links)

    def test_asset_type_and_pattern_derived_from_the_control_record(self):  # BI-W02
        code, out, f = self.imp()
        by = {i['id']: i for i in json.loads(f.read_text())['instances']}
        sd = by['SD-SAMPLE-ORDER-INITIATION']['attributes']
        self.assertEqual((sd['asset_type'], sd['functional_pattern']), ('AT-SAMPLE-ORDER-INITIATION', 'FP-TRANSACT'))
        self.assertEqual(by['FP-TRANSACT']['attributes']['generic_artefact'], 'Transaction')
        self.assertIn('derived — confirm', (self.tmp / 'a2.report.md').read_text())

    def test_underivable_domains_are_listed_and_a_table_supplies_them(self):  # BI-W02
        code, out, f = self.imp(names=('Sample Ledger Tracking', 'Sample Order Initiation'))
        self.assertEqual(code, 2); self.assertIn('Sample Ledger Tracking,<asset type>,<functional pattern>', out); self.assertFalse(f.exists())
        table = self.tmp / 'patterns.csv'
        table.write_text('service domain,asset type,functional pattern\nSample Ledger Tracking,Ledger,track\n', encoding='utf-8')
        code, out, f = self.imp('--patterns', table, names=('Sample Ledger Tracking', 'Sample Order Initiation'))
        self.assertEqual(code, 0, out)
        sd = {i['id']: i for i in json.loads(f.read_text())['instances']}['SD-SAMPLE-LEDGER-TRACKING']['attributes']
        self.assertEqual((sd['asset_type'], sd['functional_pattern']), ('AT-LEDGER', 'FP-TRACK'))
        self.assertIn('your table', (self.tmp / 'a2.report.md').read_text())
        table.write_text('Sample Ledger Tracking,Ledger,juggle\n', encoding='utf-8')
        code, out, _ = self.imp('--patterns', table, names=('Sample Ledger Tracking',))
        self.assertEqual(code, 2); self.assertIn('not a BIAN functional pattern', out)

    def test_descriptions_only_on_request(self):  # BI-W03
        made_up = 'A made-up service domain'
        self.imp(); self.assertNotIn(made_up, (self.tmp / 'a2.json').read_text())
        self.imp('--descriptions'); self.assertIn(made_up, (self.tmp / 'a2.json').read_text())

    def test_business_objects_only_on_request(self):  # BI-W04
        self.imp(); types = {i['type'] for i in json.loads((self.tmp / 'a2.json').read_text())['instances']}
        self.assertNotIn('A2.BusinessObject', types)
        self.imp('--objects'); bos = [i for i in json.loads((self.tmp / 'a2.json').read_text())['instances'] if i['type'] == 'A2.BusinessObject']
        self.assertIn('Payment', [b['name'] for b in bos]); self.assertNotIn('HTTP Error', [b['name'] for b in bos])

    def test_provenance_on_every_record(self):  # BI-W05
        code, out, f = self.imp()
        d = json.loads(f.read_text()); self.assertEqual(d['source_system'], 'BIAN-SEMANTIC-API-99.0.0')
        for i in d['instances']:
            self.assertEqual(i['version'], '99.0.0', i['id'])
            if i['type'] not in ('A2.AssetType', 'A2.FunctionalPattern'):
                self.assertEqual(i['attributes']['source_id'], 'bian-semantic-api:99.0.0:SampleOrderInitiation.yaml', i['id'])

    def test_ids_are_stable(self):  # BI-W06
        self.imp(); a = (self.tmp / 'a2.json').read_text()
        self.imp(); self.assertEqual(a, (self.tmp / 'a2.json').read_text())

    def test_checked_before_writing_and_shared_names_kept_apart(self):  # BI-W07; BIAN 14 gives two domains one control-record name
        code, out, f = self.imp(names=('Sample Twin Services', 'Sample Corporate Twin Services', 'Sample Order Initiation', 'Sample Party Directory'))
        self.assertEqual(code, 0, out); self.assertIn('checked: no errors', out)
        by = {i['id']: i for i in json.loads(f.read_text())['instances']}
        self.assertIn('CR-SAMPLE-TWIN-SERVICES', by); self.assertIn('CR-SAMPLE-CORPORATE-TWIN-SERVICES', by)
        self.assertIn('Payment (Sample Order Initiation)', [i['name'] for i in by.values()])      # qualifier names unique per domain
        self.assertIn('Control records with the same name', (self.tmp / 'a2.report.md').read_text())
        errors, _ = bian.check(json.loads(f.read_text())); self.assertEqual(errors, [])

    def test_a_failing_check_writes_nothing(self):  # BI-W07
        domains, _ = bian.read_release(SAMPLE)
        data, _ = bian.build([d for d in domains if d['name'] == 'Sample Order Initiation'], '0.4.0')
        data['instances'][0]['type'] = 'A2.NoSuchKind'
        self.assertTrue(bian.check(data)[0])
        orig = bian.check
        bian.check = lambda d: (['forced error'], [])
        try: code = bian.main(['import', str(SAMPLE), '-o', str(self.tmp / 'a2.json'), '--only', 'Sample Order Initiation'])
        finally: bian.check = orig
        self.assertEqual(code, 1); self.assertFalse((self.tmp / 'a2.json').exists()); self.assertFalse((self.tmp / 'a2.report.md').exists())

    # ---- re-import and use (BI-R01, R02)
    def test_reimport_reports_what_changed(self):  # BI-R01
        self.imp(); prev = self.tmp / 'prev.json'; shutil.copyfile(self.tmp / 'a2.json', prev)
        code, out, f = self.imp('--previous', prev, '--json', names=('Sample Party Directory',))
        res = json.loads(out)
        self.assertIn('SD-SAMPLE-PARTY-DIRECTORY', res['changes']['added']); self.assertIn('SD-SAMPLE-ORDER-INITIATION', res['changes']['dropped'])
        self.assertIn('is **not** removed from your estate', (self.tmp / 'a2.report.md').read_text())

    def test_the_output_is_a_bian_layer_sdem_load_accepts(self):  # the point: an A2 layer for onboarding
        from sdem import load, transform
        code, out, f = self.imp(names=('Sample Order Initiation', 'Sample Party Directory'))
        transform.extract(ROOT / 'examples' / 'designs' / 'confluence-folder-export', self.tmp / 'history', ocr='off')
        res = load.load(self.tmp / 'history', self.tmp / 'estate', 'jane.architect', exclude=['HIS-A3-PAYMENT-ORDER'], a2=f)
        self.assertGreater(res['reconciliation']['loaded'], 0)
        self.assertEqual(json.loads((self.tmp / 'estate' / 'a2-service-domain.json').read_text())['source_system'], 'BIAN-SEMANTIC-API-99.0.0')



class BaseBianTests(unittest.TestCase):
    """The base BIAN that ships with SDEM (docs/design/sdem-bian-base-spec.md, BB-*)."""
    def setUp(self): self.tmp = Path(tempfile.mkdtemp())
    def tearDown(self): shutil.rmtree(self.tmp, ignore_errors=True)

    def test_the_base_is_bians_release_14_without_descriptions(self):  # BB-S01, BB-S02
        f = bian.base_file(); self.assertEqual(f.name, 'base-14.0.0.json')
        p = json.loads(f.read_text(encoding='utf-8'))
        self.assertEqual((p['format'], p['release'], len(p['domains'])), (bian.PACK_FORMAT, '14.0.0', 258))
        for d in p['domains']:
            self.assertEqual(set(d), {'file', 'name', 'release', 'operations', 'control_record', 'qualifiers', 'control_record_fields'}, d['name'])
        self.assertIn('Apache License', (ROOT / 'bian' / 'LICENSE').read_text())
        readme = (ROOT / 'bian' / 'README.md').read_text()
        for must in ('github.com/bian-official/public', 'Apache License 2.0', 'left out', 'not affiliated with, endorsed by'):
            self.assertIn(must, readme)
        self.assertIn('bian/base-14.0.0.json', (ROOT / 'THIRD_PARTY.md').read_text())

    def test_import_from_the_base(self):  # BB-C01
        out = self.tmp / 'a2.json'
        code, text = sdem('import', '--base', '--only', 'Payment Order Initiation', '-o', out)
        self.assertEqual(code, 0, text); self.assertIn('BIAN release 14.0.0', text)
        d = json.loads(out.read_text())
        self.assertEqual(d['source_system'], 'BIAN-SEMANTIC-API-14.0.0')
        self.assertIn('SO-PAYMENT-ORDER-INITIATION-INITIATE', {i['id'] for i in d['instances']})
        self.assertEqual(bian.check(d)[0], [])

    def test_all_imports_what_it_can_and_lists_the_rest(self):  # BI-C07
        out = self.tmp / 'a2.json'; template = self.tmp / 'a2.needs-patterns.csv'
        code, text = sdem('import', SAMPLE, '--all', '-o', out)
        self.assertEqual(code, 0, text); self.assertIn('left out: 1 service domain(s)', text)
        names = {i['name'] for i in json.loads(out.read_text())['instances'] if i['type'] == 'A2.ServiceDomain'}
        self.assertNotIn('Sample Ledger Tracking', names); self.assertIn('Sample Order Initiation', names)
        self.assertIn('Sample Ledger Tracking,,', template.read_text())
        self.assertIn('## Left out — 1 service domain(s) need your pattern', (self.tmp / 'a2.report.md').read_text())
        code, text = sdem('import', SAMPLE, '--all', '--patterns', template, '-o', out)   # an unfilled row is "not given yet", not an error
        self.assertEqual(code, 0, text); self.assertIn('left out: 1', text)
        template.write_text(template.read_text().replace('Sample Ledger Tracking,,', 'Sample Ledger Tracking,Ledger,Track'), encoding='utf-8')
        code, text = sdem('import', SAMPLE, '--all', '--patterns', template, '-o', out)
        self.assertEqual(code, 0, text); self.assertNotIn('left out', text)
        self.assertIn('Sample Ledger Tracking', {i['name'] for i in json.loads(out.read_text())['instances'] if i['type'] == 'A2.ServiceDomain'})

    def test_all_on_the_base_bian(self):  # BI-C07 on the real base: 192 imported, 66 listed for a person to fill in
        out = self.tmp / 'a2.json'
        code, text = sdem('import', '--base', '--all', '-o', out)
        self.assertEqual(code, 0, text); self.assertIn('192 service domain(s)', text); self.assertIn('left out: 66', text)
        self.assertEqual(sum(1 for l in (self.tmp / 'a2.needs-patterns.csv').read_text().splitlines() if l.endswith(',,')), 66)

    def test_list_marks_what_needs_your_pattern(self):  # BB-C02
        code, text = sdem('list', '--base')
        self.assertEqual(code, 0); self.assertIn("66 marked 'needs your pattern'", text)
        line = next(l for l in text.splitlines() if l.strip().startswith('Virtual Account'))
        self.assertTrue(line.endswith('needs your pattern'))

    def test_pack_your_own_and_import_the_same(self):  # BB-C03, BB-C05: a pack gives exactly what its folder gives
        mine = self.tmp / 'acme-bian.json'
        code, text = sdem('pack', SAMPLE, '-o', mine)
        self.assertEqual(code, 0, text); self.assertIn('packed 5 service domain(s)', text)
        names = ('Sample Order Initiation', 'Sample Party Directory', 'Sample Twin Services')
        a, b = self.tmp / 'from-folder.json', self.tmp / 'from-pack.json'
        self.assertEqual(sdem('import', SAMPLE, '--only', *names, '-o', a)[0], 0)
        self.assertEqual(sdem('import', '--base', mine, '--only', *names, '-o', b)[0], 0)
        self.assertEqual(json.loads(a.read_text()), json.loads(b.read_text()))
        code, text = sdem('pack', BAD, '-o', self.tmp / 'x.json')
        self.assertEqual(code, 2); self.assertFalse((self.tmp / 'x.json').exists())

    def test_one_source_and_no_descriptions_from_the_base(self):  # BB-C01, BB-C04
        code, text = sdem('list'); self.assertEqual(code, 2); self.assertIn('name one BIAN source', text)
        code, text = sdem('list', SAMPLE, '--base'); self.assertEqual(code, 2)
        code, text = sdem('import', '--base', '--only', 'Payment Order Initiation', '--descriptions', '-o', self.tmp / 'x.json')
        self.assertEqual(code, 2); self.assertIn('import from BIAN', text); self.assertFalse((self.tmp / 'x.json').exists())
        code, text = sdem('list', '--base', str(self.tmp / 'missing.json')); self.assertEqual(code, 2)


if __name__ == '__main__':
    unittest.main()
