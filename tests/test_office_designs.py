"""Word, Excel and single-file designs in `sdem transform` (docs/design/sdem-transform-spec.md HI-F01…HI-F03): an Excel workbook's
tabs are read as sections — inventories on one tab, links on another — each record citing its sheet row; hidden tabs, title lines
and tabs no rule reads are reported, never guessed; a Word document's headings, tables and paragraphs are read as a Markdown page's;
one design file, or design files in the top folder, are read without a Confluence export around them. Made-up designs only."""
import json, os, shutil, subprocess, sys, tempfile, unittest, zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(Path(__file__).resolve().parent))
import office_samples   # noqa: E402
from sdem import office, transform   # noqa: E402


def sdem(*args, cwd):
    env = {**os.environ, 'PYTHONPATH': str(ROOT) + os.pathsep + os.environ.get('PYTHONPATH', '')}   # installed or not (CI is not)
    r = subprocess.run([sys.executable, '-m', 'sdem', *map(str, args)], cwd=cwd, capture_output=True, text=True, env=env)
    return r.returncode, r.stdout + r.stderr


class Base(unittest.TestCase):
    def setUp(self): self.tmp = Path(tempfile.mkdtemp())
    def tearDown(self): shutil.rmtree(self.tmp, ignore_errors=True)

    def run_on(self, src):
        x, _, issues = transform.extract(src, self.tmp / 'out', ocr='off', now='2026-11-11T00:00:00')
        doc = json.loads((self.tmp / 'out' / 'extraction.json').read_text())
        return x, doc, issues

    @staticmethod
    def where(doc, rid): return [s['where'] for r in doc['records'] if r['id'] == rid for s in r['sources']]

    @staticmethod
    def items(doc, status): return [(i['where'], i['reason']) for i in doc['coverage']['items'] if i['status'] == status]


class ExcelTests(Base):   # HI-F02
    def setUp(self):
        super().setUp(); self.book = self.tmp / 'ledger-design.xlsx'; office_samples.ledger_workbook(self.book)

    def test_each_tab_is_a_section_and_each_record_cites_its_sheet_row(self):
        _, doc, issues = self.run_on(self.book)
        types = {r['id']: r['type'] for r in doc['records']}
        self.assertEqual(types, {'HIS-A3-LEDGER-CORE': 'A3.ApplicationComponent', 'HIS-A3-REPORTING-HUB': 'A3.ApplicationComponent',
                                 'HIS-A3-RECON-ENGINE': 'A3.ApplicationComponent', 'HIS-A4-FINANCE-KUBERNETES-CLUSTER': 'A4.Node',
                                 'HIS-A4-LEDGER-DB': 'A4.SystemSoftware'})
        self.assertIn("table 1 under 'Applications', sheet row 3", self.where(doc, 'HIS-A3-LEDGER-CORE'))
        self.assertIn("table 3 under 'Infrastructure', sheet row 8", self.where(doc, 'HIS-A4-LEDGER-DB'))   # a second table on the tab
        self.assertFalse([e for k, v in issues.items() if 'advice' not in k for e in v])

    def test_links_across_tabs(self):
        _, doc, _ = self.run_on(self.book)
        flows = {(l['source'], l['target']) for l in doc['links_within'] if l['kind'] == 'flow'}
        self.assertEqual(flows, {('HIS-A3-LEDGER-CORE', 'HIS-A3-REPORTING-HUB'), ('HIS-A3-LEDGER-CORE', 'HIS-A3-RECON-ENGINE')})
        dep = [(c['source'], c['mapping_type_id'], c['target']) for c in doc['links_between_candidates']]
        self.assertEqual(dep, [('HIS-A3-LEDGER-CORE', 'COMPONENT_DEPLOYED_ON_NODE', 'HIS-A4-FINANCE-KUBERNETES-CLUSTER')])   # HL-02, the Deployment tab

    def test_what_is_not_read_is_reported(self):
        _, doc, _ = self.run_on(self.book)
        skipped, missed = self.items(doc, 'skipped'), self.items(doc, 'not captured')
        self.assertIn(("sheet 'Old'", 'a hidden sheet — not read; unhide it if it holds design data'), skipped)
        self.assertNotIn('Retired App', json.dumps(doc['records']))
        self.assertTrue(any("'Risks'" in w and 'no entity type' in r for w, r in missed))   # a tab no rule reads: never typed
        self.assertTrue(any(w == "table 1 under 'Applications'" and 'empty name' in r for w, r in skipped))
        self.assertFalse(any(r['name'] == 'Application inventory' for r in doc['records']))   # a merged title line is not the header

    def test_cells_as_excel_saved_them(self):
        blocks, title, _ = office.xlsx_blocks(self.book.read_bytes())
        self.assertEqual(title, 'General Ledger design (made up)')
        apps = next(x for k, s, x in blocks if k == 'table' and s == 'Applications')
        self.assertEqual(apps[1], ['Application', 'Description', 'Status'])
        self.assertEqual(apps[2][1], ['Reporting Hub', 'Builds financial reports', 'active'])   # a formula's saved value
        self.assertEqual(apps[3], [3, 4, 5])

    def test_deterministic(self):   # HI-G03
        a = self.run_on(self.book)[1]; shutil.rmtree(self.tmp / 'out'); b = self.run_on(self.book)[1]
        self.assertEqual(json.dumps(a['records']), json.dumps(b['records']))


class WordTests(Base):   # HI-F01
    def setUp(self):
        super().setUp(); self.doc = self.tmp / 'ledger-design.docx'; office_samples.ledger_document(self.doc)

    def test_headings_tables_and_text(self):
        _, doc, _ = self.run_on(self.doc)
        self.assertIn("table 2 under 'Application architecture', row 1", self.where(doc, 'HIS-A3-LEDGER-CORE'))
        self.assertIn("table 1 under 'Business context', row 1", self.where(doc, 'HIS-A1-GENERAL-LEDGER-MANAGEMENT'))
        self.assertEqual([(l['source'], l['kind'], l['target']) for l in doc['links_within']], [('HIS-A3-LEDGER-CORE', 'flow', 'HIS-A3-REPORTING-HUB')])
        idx = json.loads((self.tmp / 'out' / 'design-index.json').read_text())
        self.assertEqual(idx['designs'][0]['title'], 'General Ledger Solution Design (made up)')

    def test_pictures_are_reported_not_read(self):
        _, doc, _ = self.run_on(self.doc)
        self.assertTrue(any('picture' in w and 'not read' in r for w, r in self.items(doc, 'not captured')))

    def test_text_never_makes_a_record(self):   # HI-R04 holds for Word too
        _, doc, _ = self.run_on(self.doc)
        self.assertFalse(any('Finance' == r['name'] for r in doc['records']))
        self.assertEqual(len(doc['records']), 3)


class FilesAndFoldersTests(Base):   # HI-F03
    def test_design_files_in_the_top_folder(self):
        d = self.tmp / 'designs'; d.mkdir()
        office_samples.ledger_workbook(d / 'ledger.xlsx'); office_samples.ledger_document(d / 'ledger.docx')
        (d / 'apps.csv').write_text('Application,Description\nPayments Hub,Takes payments\n')
        (d / 'pages.csv').write_text('id,title,url\n1,Ledger,https://wiki.example/1\n')      # a manifest — provenance, not a design
        (d / 'README.md').write_text('# about these designs\n')
        x, doc, _ = self.run_on(d)
        self.assertEqual(sorted(p['file'] for p in x.pages), ['apps.csv', 'ledger.docx', 'ledger.xlsx'])
        self.assertEqual(sorted(f['file'] for f in x.provenance_files), ['README.md', 'pages.csv'])
        self.assertIn('HIS-A3-PAYMENTS-HUB', {r['id'] for r in doc['records']})

    def test_unreadable_office_file_is_reported_and_the_rest_read(self):
        d = self.tmp / 'designs'; d.mkdir(); office_samples.ledger_document(d / 'good.docx')
        (d / 'broken.xlsx').write_bytes(b'not a zip'); (d / 'old.xls').write_bytes(b'\xd0\xcf\x11\xe0')
        _, doc, _ = self.run_on(d)
        missed = self.items(doc, 'not captured')
        self.assertTrue(any(w == 'broken.xlsx' and 'save it as .docx or .xlsx' in r.lower() for w, r in missed), missed)
        self.assertTrue(any(w == 'old.xls' and 'save each sheet as .xlsx' in r for w, r in missed), missed)
        self.assertIn('HIS-A3-LEDGER-CORE', {r['id'] for r in doc['records']})

    def test_cli_takes_one_file(self):
        f = self.tmp / 'ledger-design.xlsx'; office_samples.ledger_workbook(f)
        code, out = sdem('transform', 'run', f, '-o', self.tmp / 'out', '--ocr', 'off', cwd=self.tmp)
        self.assertEqual(code, 0, out); self.assertIn('A3 3 records, A4 2 records', out)
        code, out = sdem('transform', 'inspect', f, '--ocr', 'off', cwd=self.tmp)
        self.assertEqual(code, 0, out); self.assertIn('[application | runs on | environment] → HL-02', out)
        (self.tmp / 'notes.pdf').write_bytes(b'%PDF')
        code, out = sdem('transform', 'run', self.tmp / 'notes.pdf', '-o', self.tmp / 'o2', cwd=self.tmp)
        self.assertEqual(code, 2); self.assertIn('SDEM reads designs in', out)

    def test_an_office_file_is_a_zip_of_xml_only(self):   # no macros run, nothing executed: only XML parts are read
        f = self.tmp / 'x.xlsx'; office_samples.ledger_workbook(f)
        with zipfile.ZipFile(f, 'a') as z: z.writestr('xl/vbaProject.bin', b'\x00' * 10)
        blocks, _, _ = office.xlsx_blocks(f.read_bytes())
        self.assertTrue(blocks)


if __name__ == '__main__':
    unittest.main()
