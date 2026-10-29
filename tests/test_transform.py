"""`sdem transform`: a Confluence HTML export of past designs → candidate architecture records (spec docs/design/sdem-transform-spec.md).
Run against the synthetic export in tests/fixtures/confluence-export-sample (scripts/make_confluence_sample.py)."""
import json, re, shutil, sys, tempfile, unittest
from pathlib import Path

from sdem import transform
from sdem.graph import LevelGraph
from sdem.metamodel import Metamodel

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / 'tests' / 'fixtures' / 'confluence-export-sample'
KNOWN = ROOT / 'examples' / 'payment-initiation' / 'a3-application.json'
FOLDER = ROOT / 'examples' / 'designs' / 'confluence-folder-export'


class TransformTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        cls.x, cls.ds, cls.issues = transform.extract(SAMPLE, cls.tmp / 'out', known=[KNOWN], now='2026-10-28T00:00:00', ocr='off')
        cls.doc = json.loads((cls.tmp / 'out' / 'extraction.json').read_text())
        cls.by_name = {r['name']: r for r in cls.doc['records']}

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_tables_become_records(self):  # HI-R01
        r = self.by_name['Fraud Screening']
        self.assertEqual(r['type'], 'A3.ApplicationComponent'); self.assertEqual(r['confidence'], 'medium')
        self.assertEqual(r['sources'][0]['rule'], 'HT-01')
        self.assertEqual(self.by_name['Payment Initiation']['type'], 'A1.BusinessCapability')
        self.assertEqual(self.by_name['PAYDB01']['type'], 'A4.Node')
        a3 = {i['name']: i for i in self.ds['A3']['instances']}
        self.assertEqual(a3['Fraud Screening']['lifecycle_status'], 'planned')
        self.assertEqual(a3['Legacy Payment Forms']['lifecycle_status'], 'retired')
        self.assertEqual(a3['Fraud Screening']['attributes']['vendor'], 'VendorCo')

    def test_every_kind_of_drawio_file_is_read(self):  # HI-R02: plain XML without extension, compressed, PNG with the diagram inside
        files = {d['file'] for p in json.loads((self.tmp / 'out' / 'design-index.json').read_text())['designs'] for d in p['diagrams']}
        self.assertEqual(files, {'attachments/1001/1001', 'attachments/1002/3001.drawio', 'attachments/1002/3002.png'})
        self.assertEqual(self.by_name['Payment Initiation Service']['type'], 'A3.ApplicationService')   # ArchiMate shape
        self.assertEqual(self.by_name['Alerts DB']['type'], 'A4.SystemSoftware')                      # label word in a compressed diagram
        self.assertEqual(self.by_name['Fraud AWS EKS Cluster']['type'], 'A4.Node')                    # diagram inside a PNG
        self.assertNotIn('Payments Hub — application view', self.by_name)                             # a text box is not a record

    def test_lines_and_containment(self):  # HI-R03
        links = {(l['source'], l['kind'], l['target']) for l in self.doc['links_within']}
        self.assertIn(('HIS-A3-PAYMENTS-HUB', 'flow', 'HIS-A3-EXECUTION-GATEWAY'), links)
        self.assertIn(('HIS-A3-FRAUD-SCORING-ENGINE', 'triggering', 'HIS-A3-CASE-MANAGEMENT-SYSTEM'), links)
        self.assertIn(('HIS-A3-PAYMENTS-HUB', 'flow', 'HIS-A3-FRAUD-SCREENING'), links)            # source/target table
        cross = {(c['source'], c['target'], c['mapping_type_id']) for c in self.doc['links_between_candidates']}
        self.assertIn(('HIS-A3-LEDGER-POSTING-SERVICE', 'HIS-A4-PAYMENTS-KUBERNETES-CLUSTER', 'COMPONENT_DEPLOYED_ON_INFRASTRUCTURE'), cross)
        self.assertEqual(len(cross), len(self.doc['links_between_candidates']))                   # merged, not repeated
        gw = next(c for c in self.doc['links_between_candidates'] if c['source'] == 'HIS-A3-EXECUTION-GATEWAY')
        self.assertEqual(len(gw['sources']), 2)                                                     # the diagram and the text
        for l in self.doc['links_within']:  # every kind is one the metamodel allows
            a = next(r for r in self.doc['records'] if r['id'] == l['source']); b = next(r for r in self.doc['records'] if r['id'] == l['target'])
            self.assertIsNone(Metamodel.load().relationship_issue(a['type'][:2], a['type'], l['kind'], b['type']))

    def test_narrative_uses_known_names_only(self):  # HI-R04
        links = {(l['source'], l['kind'], l['target']): l for l in self.doc['links_within']}
        l = links[('HIS-A3-PAYMENTS-HUB', 'serving', 'HIS-A3-MOBILE-BANKING-APP')]          # "the App calls the Hub": the Hub serves the App
        self.assertEqual(l['confidence'], 'low'); self.assertEqual(l['sources'][0]['rule'], 'HP-02')
        self.assertNotIn('Branch Payment Forms', self.by_name)                               # words in text never create records
        self.assertEqual(self.by_name['Payment Initiation Service']['same_as_existing']['id'], 'SVC-PAY-INIT')

    def test_pictures_and_unknown_shapes_go_to_a_person(self):  # HI-R05
        what = [(v['what'], v.get('name')) for v in self.doc['for_review']]
        self.assertIn(('picture', 'rack-photo'), what)
        self.assertIn(('shape', 'Card Authorisation Switch'), what)
        self.assertEqual(sum(1 for w, _ in what if w == 'picture'), 1)   # draw.io previews and emoticons are not reported

    def test_candidates_never_above_medium_and_carry_their_source(self):  # HI-C01, HI-C02
        for r in self.doc['records']:
            self.assertEqual(r['status'], 'candidate'); self.assertIn(r['confidence'], ('low', 'medium'))
            for s in r['sources']:
                self.assertTrue(s['page_id'] and s['where'] and s['rule'] and s['reasoning'])
        for d in self.ds.values():
            self.assertEqual(d['source_system'], 'CONFLUENCE-EXTRACT')
            for i in d['instances']: self.assertTrue(i['attributes']['source_id'].startswith('confluence:'))

    def test_candidate_datasets_pass_sdem_check(self):  # HI-C03
        for lvl, d in self.ds.items():
            self.assertEqual(LevelGraph(d, Metamodel.load()).validate(), [], lvl)
        self.assertEqual(self.ds['A3']['instances'][0]['version'][:2], '20')   # the page's last-modified date

    def test_design_index_and_report(self):  # HI-O02, HI-O03
        idx = {p['page_id']: p for p in json.loads((self.tmp / 'out' / 'design-index.json').read_text())['designs']}
        self.assertEqual(set(idx), {'1001', '1002'})
        self.assertEqual(idx['1002']['modified'], '2019-06-03'); self.assertEqual(idx['1001']['title'], 'Payments Hub Solution Design')
        self.assertIn('HIS-A3-PAYMENTS-HUB', idx['1001']['records'])
        rep = (self.tmp / 'out' / 'extraction-report.md').read_text()
        for part in ('## Records', '## Links between architectures', '## For a person', '## Designs'): self.assertIn(part, rep)

    def test_deterministic(self):  # HI-G03
        out2 = self.tmp / 'again'
        transform.extract(SAMPLE, out2, known=[KNOWN], now='2026-10-28T00:00:00', ocr='off')
        for f in ('a3-application.json', 'extraction.json', 'design-index.json', 'extraction-report.md'):
            self.assertEqual((self.tmp / 'out' / f).read_text().replace(str(self.tmp / 'out'), ''), (out2 / f).read_text().replace(str(out2), ''), f)

    def test_rules_file_tunes_without_code(self):  # HI-G02
        rules = json.loads(transform.RULES.read_text())
        rules['label_words']['A3.ApplicationComponent'].append('switch')
        p = self.tmp / 'rules.json'; p.write_text(json.dumps(rules))
        x, _, _ = transform.extract(SAMPLE, self.tmp / 'tuned', rules=p, now='2026-10-28T00:00:00', ocr='off')
        names = {r['name'] for r in x.records.values()}
        self.assertIn('Card Authorisation Switch', names)
        self.assertFalse(any(v.get('name') == 'Card Authorisation Switch' for v in x.review))

    def test_inspect_shows_structure(self):  # HI-I01
        r = transform.inspect(SAMPLE, ocr='off')
        rules = {tuple(t['columns']): t['rule'] for t in r['tables']}
        self.assertEqual(rules[('application', 'description', 'vendor', 'status')], 'HT-01')
        self.assertTrue(any(t['rule'] == 'page facts' for t in r['tables']))   # the key-value table (HI-N04)
        self.assertTrue(any(s['type'] == 'unclassified' for s in r['shapes']))

    def test_no_ai_no_network(self):  # HI-G01
        src = (ROOT / 'sdem' / 'transform.py').read_text()
        self.assertIsNone(re.search(r'\bimport (socket|requests|http\.client)|urllib\.request|anthropic|openai', src))

    def test_unmapped_link_column_kept(self):  # HI-N03 on a source/target table: 'Protocol' stays with the link
        link = next(l for l in self.doc['links_within'] if l['source'] == 'HIS-A3-PAYMENTS-HUB' and l['target'] == 'HIS-A3-FRAUD-SCREENING')
        self.assertEqual(link['unmapped'], {'Protocol': 'REST'})

    def test_cli(self):
        from sdem.cli import main
        self.assertEqual(main(['transform', 'run', str(SAMPLE), '-o', str(self.tmp / 'cli'), '--json', '--ocr', 'off']), 0)
        self.assertTrue((self.tmp / 'cli' / 'a3-application.json').exists())
        self.assertEqual(main(['transform', 'run', str(self.tmp / 'missing'), '-o', str(self.tmp / 'x')]), 2)



    def test_never_creates_a2_entities(self):  # HI-S01, CTL-24: BIAN elements come from a BIAN source only
        a2 = ROOT / 'examples' / 'payment-initiation' / 'a2-service-domain.json'
        names = [i['name'] for i in json.loads(a2.read_text())['instances'] if i['type'] == 'A2.ServiceDomain'][:1]
        tmp = Path(tempfile.mkdtemp())
        try:
            src = tmp / 'export' / 'Design' / '2. Application'; src.mkdir(parents=True)
            (src / 'page.md').write_text(f"# Design\n\n| Application | Description |\n|---|---|\n| {names[0]} | a BIAN domain named in a table |\n")
            x, ds, _ = transform.extract(tmp / 'export', tmp / 'o', known=[a2], now='2026-10-28T00:00:00', ocr='off')
            self.assertNotIn('A2', ds)
            self.assertFalse(any(r['type'].startswith('A2.') for r in x.records.values()))
            rules = json.loads(transform.RULES.read_text()); rules['tables'][0]['type'] = 'A2.ServiceDomain'   # even a rules file that asks for A2
            rp = tmp / 'r.json'; rp.write_text(json.dumps(rules))
            x2, ds2, _ = transform.extract(tmp / 'export', tmp / 'o2', rules=rp, now='2026-10-28T00:00:00', ocr='off')
            self.assertNotIn('A2', ds2); self.assertEqual(x2.bian_mentions[0]['name'], names[0])
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class FolderLayoutTests(unittest.TestCase):
    """A prepared export: readme/source/evidence in the root, raw HTML and diagrams in archives/, sections as folders (HI-L*)."""
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        cls.x, cls.ds, cls.issues = transform.extract(FOLDER, cls.tmp / 'out', now='2026-10-28T00:00:00', ocr='off')
        cls.doc = json.loads((cls.tmp / 'out' / 'extraction.json').read_text())
        cls.idx = {p['file']: p for p in json.loads((cls.tmp / 'out' / 'design-index.json').read_text())['designs']}
        cls.by_name = {r['name']: r for r in cls.doc['records']}

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_pages_found_in_any_folder_and_format(self):  # HI-L01
        self.assertEqual({f for f, p in self.idx.items() if not p['diagram_only']}, {
            'archives/payments-hub-design.html', 'Payments Hub Design/1. Business Context/overview.md',
            'Payments Hub Design/2. Application Architecture/integrations.html', 'Payments Hub Design/2. Application Architecture/notes.txt',
            'Payments Hub Design/2. Application Architecture/container-view.md',
            'Payments Hub Design/3. Infrastructure/servers.csv'})
        self.assertEqual(self.by_name['Payment Initiation']['type'], 'A1.BusinessCapability')     # Markdown table
        self.assertEqual(self.by_name['PAYAPP02']['type'], 'A4.Node')                              # CSV
        self.assertIn('Payments Hub Design / Infrastructure', self.by_name['PAYAPP02']['sources'][0]['where'])   # folders as sections, numbers dropped

    def test_root_files_are_provenance_and_fill_in_the_page(self):  # HI-L02
        prov = {f['file']: f for f in self.doc['provenance_files']}
        self.assertEqual(set(prov), {'README.md', 'source.json', 'evidence.csv'})
        self.assertEqual(prov['source.json']['pages_matched'], 1); self.assertTrue(prov['README.md']['sha256'])
        page = self.idx['archives/payments-hub-design.html']
        self.assertEqual(page['page_id'], '55501'); self.assertIn(page['page_id_from'], ('source.json', 'evidence.csv'))   # both list it
        self.assertEqual(page['modified'], '2022-05-10'); self.assertTrue(page['url'].endswith('/55501'))

    def test_diagram_the_html_refers_to_is_linked_to_its_page(self):  # HI-L03
        page = self.idx['archives/payments-hub-design.html']
        self.assertEqual(sorted(d['file'] for d in page['diagrams']), ['archives/diagrams/hub-context.png', 'archives/diagrams/payment-sequence.svg', 'archives/diagrams/payments-components.png'])
        self.assertEqual(self.by_name['Payment Order']['sources'][0]['page_id'], '55501')
        self.assertFalse(any(v['what'] == 'picture' and 'hub-context' in v['where'] for v in self.doc['for_review']))

    def test_unlinked_diagrams_are_read_with_their_folder(self):  # HI-L04
        nl = {v['where'] for v in self.doc['for_review'] if v['what'] == 'diagram not linked to a page'}
        self.assertEqual(nl, {'archives/diagrams/network-zones.drawio', 'Payments Hub Design/3. Infrastructure/infrastructure.svg', 'Payments Hub Design/3. Infrastructure/deployment.puml'})
        sw = self.by_name['Core Switch']
        self.assertEqual(sw['type'], 'A4.Node'); self.assertIn('Infrastructure', sw['sources'][0]['reasoning'])
        self.assertEqual(self.by_name['PAYAPP01']['type'], 'A4.Node')        # the name from the servers table wins over the label word "app"
        self.assertNotIn(('same name, different types', 'PAYAPP01'), {(v['what'], v.get('name')) for v in self.doc['for_review']})

    def test_pictures_shown_or_not_go_to_a_person(self):  # HI-L05
        what = {(v['what'], v.get('name')) for v in self.doc['for_review']}
        self.assertIn(('picture', 'customer journey sketch'), what)
        self.assertIn(('picture not shown on any page', 'rack-photo.jpg'), what)

    def test_inspect_layout_and_anonymous(self):  # HI-I02
        r = transform.inspect(FOLDER, ocr='off')
        folders = {f['folder']: f for f in r['layout']}
        self.assertEqual(folders['.']['provenance'], 3); self.assertEqual(folders['archives/diagrams']['diagram'], 4)
        a = transform.inspect(FOLDER, anonymous=True, ocr='off')
        text = json.dumps(a)
        self.assertNotIn('Payments', text); self.assertNotIn('Infrastructure', text); self.assertIn('archives/diagrams', text)
        self.assertNotIn('tables', a); self.assertNotIn('headings', a)

    def test_deployed_on_written_as_data(self):  # HI-R06: the form the engine reads
        a3 = {i['name']: i for i in self.ds['A3']['instances']}
        self.assertEqual(a3['Clearing Gateway']['attributes']['deployed_on'], ['HIS-A4-PAYAPP01'])           # "is hosted on" in the text
        self.assertEqual(a3['Payments Hub']['attributes']['deployed_on'], ['HIS-A4-PAYMENTS-KUBERNETES-CLUSTER'])  # nested in the node
        self.assertNotIn('deployed_on', a3['Mobile Banking App'].get('attributes', {}))

    def test_plantuml_in_every_form(self):  # HI-P01: PNG with the source inside, encoded SVG, Markdown code block, .puml file
        kinds = {d['file']: d.get('kind') for p in self.idx.values() for d in p['diagrams']}
        self.assertEqual(kinds['archives/diagrams/payments-components.png'], 'plantuml')
        self.assertEqual(kinds['archives/diagrams/payment-sequence.svg'], 'plantuml')
        self.assertEqual(kinds['Payments Hub Design/2. Application Architecture/container-view.md#plantuml-1'], 'plantuml')
        self.assertEqual(kinds['Payments Hub Design/3. Infrastructure/deployment.puml'], 'plantuml')
        t = {n: self.by_name[n]['type'] for n in ('Retail Customer', 'Sanctions Screening', 'Payments Store', 'Mobile Banking App', 'PostgreSQL 15', 'Edge Firewall')}
        self.assertEqual(t, {'Retail Customer': 'A1.BusinessActor', 'Sanctions Screening': 'A3.ApplicationComponent', 'Payments Store': 'A4.SystemSoftware',
                             'Mobile Banking App': 'A3.ApplicationComponent', 'PostgreSQL 15': 'A4.SystemSoftware', 'Edge Firewall': 'A4.Device'})
        self.assertNotIn('Bank', self.by_name)                                                       # a C4 boundary is a group, not a record

    def test_plantuml_relations_and_nesting(self):  # HI-P02
        links = {(l['source'], l['kind'], l['target']) for l in self.doc['links_within']}
        self.assertIn(('HIS-A3-SANCTIONS-SCREENING', 'serving', 'HIS-A3-PAYMENTS-HUB'), links)       # "hub --> sanc : calls"
        self.assertIn(('HIS-A3-MOBILE-BANKING-APP', 'flow', 'HIS-A3-PAYMENTS-HUB'), links)           # C4 Rel "Sends payment to"
        cross = {(c['source'], c['mapping_type_id'], c['target']) for c in self.doc['links_between_candidates']}
        self.assertIn(('HIS-A3-PAYMENTS-HUB', 'COMPONENT_DEPLOYED_ON_INFRASTRUCTURE', 'HIS-A4-PAYMENTS-KUBERNETES-CLUSTER'), cross)   # nested in the node
        self.assertIn(('HIS-A3-PAYMENTS-HUB', None, 'HIS-A4-PAYMENTS-STORE'), cross)                 # uses a database: not a deployment

    def test_plantuml_parser_notations(self):  # HI-P03
        els, rels, kind = transform.plantuml_parse("""@startuml
participant "Mobile App" as M
alt ok
M -> P : submit
end
[Hub] <-- M
Rel_Serving(M, P, "x")
@enduml""")
        self.assertEqual(els['M']['name'], 'Mobile App'); self.assertIn(('M', 'Hub', '', 'line'), rels)   # '<--' points left
        self.assertIn(('M', 'P', 'x', 'Rel_Serving'), rels)
        self.assertEqual(transform.plantuml_parse('@startmindmap\n* a\n@endmindmap')[2], 'mindmap')
        self.assertEqual(transform.plantuml_decode('SyfFKj2rKt3CoKnELR1Io4ZDoSa70000'), 'Bob -> Alice : hello')   # PlantUML's own documented example


    # ---- nothing silently lost (HI-N01…N06)
    def test_every_item_accounted_for(self):  # HI-N01 — counted independently of the ledger
        led = self.doc['coverage']['items']
        page = transform.read_page(FOLDER / 'archives' / 'payments-hub-design.html', FOLDER, json.loads(transform.RULES.read_text()))
        mine = [i for i in led if i['file'] == 'archives/payments-hub-design.html']
        self.assertEqual(sum(1 for b in page['blocks'] if b[0] == 'table'), sum(1 for i in mine if i['kind'] == 'table'))
        self.assertEqual(sum(1 for b in page['blocks'] if b[0] == 'text'), sum(1 for i in mine if i['kind'] == 'paragraph'))
        xml = (FOLDER / 'archives' / 'diagrams' / 'network-zones.drawio').read_text()
        cells = transform.mx_cells(transform.mx_pages(xml)[0][1])
        dia = [i for i in led if 'network-zones.drawio' in i['where']]
        self.assertEqual(sum(1 for c in cells if c.get('vertex') == '1'), sum(1 for i in dia if i['kind'] == 'shape'))
        self.assertEqual(sum(1 for c in cells if c.get('edge') == '1'), sum(1 for i in dia if i['kind'] == 'line'))
        accounted = {i['file'] for i in led} | {d['file'] for p in self.idx.values() for d in p['diagrams']} | set(self.idx)
        for f in FOLDER.rglob('*'):
            if f.is_file():
                rel = f.relative_to(FOLDER).as_posix()
                self.assertTrue(rel in accounted or any(rel in i['where'] for i in led), f'{rel}: not accounted for')
        for i in led: self.assertIn(i['status'], ('captured', 'skipped', 'not captured'))
        for i in led:
            if i['status'] == 'not captured': self.assertTrue(i.get('category'), i)
            if i['status'] == 'skipped': self.assertTrue(i['reason'], i)

    def test_rules_command_writes_sdems_rules_and_never_overwrites(self):  # so a workspace repository need not find metamodel/
        import subprocess, sys, tempfile
        d = Path(tempfile.mkdtemp()); out = d / 'rules' / 'transform-rules.json'
        run = lambda: subprocess.run([sys.executable, '-m', 'sdem', 'transform', 'rules', '-o', str(out)], cwd=ROOT, capture_output=True, text=True)
        r = run(); self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(out.read_text(encoding='utf-8'), (ROOT / 'metamodel' / 'transform-rules.json').read_text(encoding='utf-8'))
        out.write_text('{"tuned": true}', encoding='utf-8')
        r = run(); self.assertEqual(r.returncode, 2); self.assertEqual(out.read_text(), '{"tuned": true}')

    def test_coverage_by_kind(self):  # HI-N02: what rules read, apart from what needs AI or a person
        from sdem.transform import coverage
        led = [{'page_id': 'p', 'page_title': 'P', 'file': 'f', 'kind': k, 'status': st} for k, st in
               (('table', 'captured'), ('shape', 'captured'), ('line', 'captured'), ('column', 'not captured'), ('paragraph', 'not captured'), ('picture', 'skipped'))]
        c = coverage(led)['by_kind']
        self.assertEqual(c['tables and diagrams']['percent'], 75); self.assertEqual(c['text']['percent'], 0)
        self.assertEqual(c['pictures']['skipped'], 1); self.assertNotIn('files', c)

    def test_coverage_reported(self):  # HI-N02
        o = self.doc['coverage']['overall']
        self.assertEqual(o['captured'] + o['skipped'] + o['not_captured'], o['items'])
        self.assertEqual(o['percent'], round(100 * o['captured'] / (o['captured'] + o['not_captured'])))
        self.assertIn('percent', self.idx['archives/payments-hub-design.html']['coverage'])
        rep = (self.tmp / 'out' / 'extraction-report.md').read_text()
        self.assertIn('## Coverage — nothing silently lost', rep); self.assertIn(f"**{o['percent']}% captured**", rep)
        self.assertIn('Coverage:', run_inspect(FOLDER))

    def test_unmapped_columns_kept(self):  # HI-N03
        hub = next(r for r in self.doc['records'] if r['name'] == 'Payments Hub')
        self.assertEqual(hub['unmapped'], {'Support hours': '24x7'})
        self.assertTrue(any(i.get('category') == 'column not mapped' and 'Support hours' in i['where'] for i in self.doc['coverage']['items']))

    def test_key_value_table_becomes_page_facts(self):  # HI-N04
        facts = self.idx['archives/payments-hub-design.html']['facts']
        self.assertEqual(facts['Owner'], 'Payments architecture team'); self.assertEqual(facts['Review date'], '2022-05-01')

    def test_no_entity_type_reported_not_forced(self):  # HI-N05
        risk = [i for i in self.doc['coverage']['items'] if i.get('category') == 'no entity type']
        self.assertEqual(len(risk), 1); self.assertIn('Clearing file late', risk[0]['text']); self.assertIn("'risk'", risk[0]['reason'])
        self.assertNotIn('Clearing file late', self.by_name)

    def test_not_captured_section_and_files(self):  # HI-N06
        rep = (self.tmp / 'out' / 'extraction-report.md').read_text()
        self.assertIn('## Not captured', rep); self.assertIn('### file not read (1)', rep); self.assertIn('payments-hub-design', rep)
        pdf = [i for i in self.doc['coverage']['items'] if i['file'] == 'archives/legacy/payments-hld-v1.pdf']
        self.assertEqual([(i['status'], i['category']) for i in pdf], [('not captured', 'file not read')])
        para = [i for i in self.doc['coverage']['items'] if i['kind'] == 'paragraph' and 'two review rounds' in i.get('text', '')]
        self.assertEqual(para[0]['category'], 'text not read')


def run_inspect(folder):
    import contextlib, io
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf): transform.main(['inspect', str(folder), '--ocr', 'off'])
    return buf.getvalue()


class OcrTests(unittest.TestCase):
    """Text read from pictures: grouping and typing tested with a stand-in engine everywhere; the real macOS engine where present (HI-O*)."""
    LINES = [{'text': 'Payments Hub', 'confidence': 0.99, 'x': 0.1, 'y': 0.10, 'w': 0.2, 'h': 0.04},
             {'text': 'Java service', 'confidence': 0.95, 'x': 0.12, 'y': 0.145, 'w': 0.16, 'h': 0.03},       # second line of the same box
             {'text': 'clearing file', 'confidence': 0.99, 'x': 0.45, 'y': 0.09, 'w': 0.1, 'h': 0.03},       # a caption on a line
             {'text': 'Payments Kubernetes Cluster', 'confidence': 0.98, 'x': 0.35, 'y': 0.55, 'w': 0.4, 'h': 0.04},
             {'text': 'Zx', 'confidence': 0.2, 'x': 0.9, 'y': 0.9, 'w': 0.02, 'h': 0.02}]

    def test_grouping_and_filters(self):
        labels = transform.group_labels(self.LINES, json.loads(transform.RULES.read_text()))
        self.assertEqual([(l['name'], l['desc']) for l in labels], [('Payments Hub', 'Java service'), ('Payments Kubernetes Cluster', '')])

    def test_stand_in_engine_makes_low_candidates_and_a_review_item(self):
        tmp = Path(tempfile.mkdtemp())
        try:
            fake = lambda path: self.LINES
            x, _, _ = transform.extract(FOLDER, tmp / 'o', now='2026-10-28T00:00:00', ocr=fake)
            doc = json.loads((tmp / 'o' / 'extraction.json').read_text())
            k8s = next(r for r in doc['records'] if r['name'] == 'Payments Kubernetes Cluster')
            self.assertTrue(any(s['rule'].startswith('HO-') and s['confidence'] == 'low' for s in k8s['sources']))
            wb = next(v for v in doc['for_review'] if v.get('name') == 'whiteboard')
            self.assertIn('read 2 label(s) by OCR', wb['why']); self.assertIn('adds the links', wb['why'])
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_tesseract_tsv(self):
        tsv = 'level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext\n' \
              '1\t1\t0\t0\t0\t0\t0\t0\t1000\t500\t-1\t\n' \
              '5\t1\t1\t1\t1\t1\t100\t50\t80\t20\t96\tPayments\n5\t1\t1\t1\t1\t2\t190\t50\t50\t20\t90\tHub\n'
        l = transform.tesseract_lines(tsv)
        self.assertEqual(l[0]['text'], 'Payments Hub'); self.assertAlmostEqual(l[0]['x'], 0.1); self.assertAlmostEqual(l[0]['confidence'], 0.93)

    def test_svg_text_is_read_without_ocr(self):
        lines = transform.svg_text_lines(b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><text x="10" y="20" font-size="10">Core <tspan>Ledger</tspan></text></svg>')
        self.assertEqual(lines[0]['text'], 'Core Ledger')

    @unittest.skipUnless(sys.platform == 'darwin' and shutil.which('osascript'), 'macOS Vision is only on macOS')
    def test_macos_vision_reads_the_whiteboard(self):
        engine = transform.ocr_engine('vision')
        try: lines = engine(FOLDER / 'Payments Hub Design' / '2. Application Architecture' / 'whiteboard.png')
        except OSError as e: self.skipTest(f'Vision not usable here: {e}')
        texts = {l['text'] for l in lines}
        self.assertIn('Payments Hub', texts); self.assertIn('Payments Kubernetes Cluster', texts)

if __name__ == '__main__':
    unittest.main()
