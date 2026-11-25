"""The authoring guide — one file an outside author (an AI assistant without the CLI) is given to write a full design as SDEM data
(docs/design/sdem-authoring-guide-design.md AU-01…AU-06). Its vocabulary and what-SDEM-checks sections are generated, so they cannot
drift from the metamodel or the shipped standards. Proof it works: files written to it load with nothing refused."""
import json, os, re, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from sdem import authorguide  # noqa: E402
from sdem.metamodel import Metamodel  # noqa: E402

ENV = {**os.environ, 'PYTHONPATH': str(ROOT) + os.pathsep + os.environ.get('PYTHONPATH', '')}


class Guide(unittest.TestCase):
    @classmethod
    def setUpClass(cls):   # the kept guide is a generated document: the core's (BX-15) — as sdem model regenerate makes it
        sys.path.insert(0, str(Path(__file__).resolve().parent)); import core_docs; core_docs.enter()
        cls.text = authorguide.render(); cls.mm = Metamodel.base()

    @classmethod
    def tearDownClass(cls):
        import core_docs; core_docs.leave()

    def test_the_command_prints_it_and_the_kept_copy_is_current(self):   # AU-01, AU-06
        r = subprocess.run([sys.executable, '-m', 'sdem', 'types', 'authoring'], capture_output=True, text=True, env={**ENV, 'SDEM_CORE_DOCS': '1'}, cwd=ROOT)   # the core's, as kept
        self.assertEqual(r.returncode, 0, r.stderr); self.assertEqual(r.stdout.rstrip('\n'), self.text.rstrip('\n'))
        self.assertEqual((ROOT / 'docs' / 'reference' / 'authoring-guide.md').read_text(encoding='utf-8'), self.text)
        with tempfile.TemporaryDirectory() as t:
            f = Path(t) / 'g.md'
            r = subprocess.run([sys.executable, '-m', 'sdem', 'types', 'authoring', '-o', f], capture_output=True, text=True, env={**ENV, 'SDEM_CORE_DOCS': '1'}, cwd=ROOT)
            self.assertEqual(r.returncode, 0, r.stderr); self.assertEqual(f.read_text(encoding='utf-8'), self.text)

    def test_it_stands_alone_method_files_rules_checks(self):   # AU-02
        for h in ('## 1. What you hand over', '## 2. The method', '## 3. The rules', '## 4. What SDEM will check', '## 5. The vocabulary', '## 6. Links between layers', '## 7. Before you hand over', '## 8. Better than the checklist'):
            self.assertIn(h, self.text)
        for f in ('a1-business.json', 'a3-application.json', 'a4-technology.json', 'BIAN-DOMAINS.json', 'CROSS-LAYER-SUGGESTIONS.json', 'NOT-STATED.json', 'CHECKLIST.json'):
            self.assertIn(f, self.text)
        for rule in ('never write the A2 file', 'Never a placeholder', 'never written in a layer file', 'You are translating a design into data. You are not designing, and you do not fill gaps',
                     'you do not decide it and you do not guess it', 'Do not invent, do not decide, do not complete', 'until it prints `OK`'):   # AU-08: translate only; SDEM's rules complete
            self.assertIn(rule, self.text)
        self.assertNotIn('DECISIONS.json', self.text)   # an author decides nothing
        for rule in ('NOT-STATED.json',):
            self.assertIn(rule, self.text)

    def test_every_type_an_author_may_write_is_there_with_its_allowed_values(self):   # AU-03
        for t, e in self.mm.entities.items():
            if e['level'] in ('A1', 'A3', 'A4') and not e.get('artefact'): self.assertIn(f'#### {t}', self.text)
        self.assertNotIn('#### A2.', self.text)                                      # BIAN is named, never written
        self.assertIn('`OpenAPI 3.1`', self.text); self.assertIn('`dmz`', self.text)   # allowed values, spelled as SDEM has them

    def test_every_link_it_lists_is_one_the_metamodel_allows(self):   # AU-03
        seen = 0
        for block in self.text.split('#### ')[1:]:
            t = block.split()[0]
            m = re.search(r'\*\*Links from it:\*\* (.*)', block)
            if not m or not self.mm.known(t): continue
            for part in m.group(1).rstrip('.').split('; '):
                kind, targets = re.match(r'`(\w+)` → (.*)', part).groups()
                for x in targets.split(', '):
                    self.assertIsNone(self.mm.relationship_issue(t.split('.')[0], t, kind, f"{t.split('.')[0]}.{x}"), f'{t} {kind} {x}'); seen += 1
        self.assertGreater(seen, 100)

    def test_what_sdem_checks_is_the_shipped_standard_and_patterns(self):   # AU-04
        std = json.loads((ROOT / 'standards' / 'sdem-completeness.json').read_text(encoding='utf-8'))
        for r in std['rules']: self.assertIn(f"| {r['id']} | {r['entity']} |", self.text)
        for title in ('Payment initiation', 'BIAN Transact', 'BIAN Fulfill'): self.assertNotIn(f'**{title}', self.text)   # BX-15: sdem-bian's patterns, in its guide when installed

    def test_the_links_between_layers_are_the_registrys(self):   # AU-03
        from sdem.validate import load_registry
        for r in load_registry()['relationships']:
            if r['source_type'].split('.')[0] in ('A1', 'A3', 'A4') or r['target_type'].split('.')[0] in ('A1', 'A3', 'A4'):
                self.assertIn(f"| {r['source_type']} | `{r['relationship']}` | {r['target_type']} |", self.text)


class Kit(unittest.TestCase):
    def test_the_kit_is_the_guide_and_an_sdem_the_author_can_run_the_check_from(self):   # AU-07, IN-02
        import shutil, zipfile
        tmp = Path(tempfile.mkdtemp()); self.addCleanup(shutil.rmtree, tmp, True)
        r = subprocess.run([sys.executable, '-m', 'sdem', 'types', 'authoring', '--kit', tmp / 'kit'], capture_output=True, text=True, env=ENV, cwd=ROOT)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual((tmp / 'kit' / 'sdem-authoring-guide.md').read_text(encoding='utf-8'), authorguide.render())
        z = next((tmp / 'kit').glob('sdem-*.zip')); zipfile.ZipFile(z).extractall(tmp / 'sdem')
        pkg = tmp / 'pkg'; pkg.mkdir()
        R = lambda i, t, n: {'id': i, 'type': t, 'version': '1', 'name': n, 'lifecycle_status': 'planned', 'attributes': {}}
        for name, doc in (('a1-business.json', {'level': 'A1', 'instances': [R('P-1', 'A1.BusinessProcess', 'Do it'), R('R-1', 'A1.BusinessRequirement', 'It is done')], 'relationships': [{'source': 'P-1', 'kind': 'realization', 'target': 'R-1'}]}),
                          ('a3-application.json', {'level': 'A3', 'instances': [R('APP-1', 'A3.Gadget', 'App')], 'relationships': []}), ('a4-technology.json', {'level': 'A4', 'instances': [], 'relationships': []}),
                          ('BIAN-DOMAINS.json', {'service_domains': []}), ('CROSS-LAYER-SUGGESTIONS.json', {'suggestions': []}), ('NOT-STATED.json', {'items': []})):
            (pkg / name).write_text(json.dumps(doc), encoding='utf-8')
        clean = {'PATH': os.environ.get('PATH', '')}   # as an outside author has it: no SDEM installed, nothing on the path but Python
        r = subprocess.run([sys.executable, '-m', 'sdem', 'intake', pkg, '--check'], capture_output=True, text=True, env=clean, cwd=tmp / 'sdem')
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr); self.assertIn('A3.Gadget', r.stdout); self.assertIn('1 thing(s) to fix', r.stdout)


if __name__ == '__main__':
    unittest.main()
