"""Metamodel extensions (docs/design/sdem-metamodel-extensions-spec.md, MX-01…MX-11a; the layer registry's LR-11): an installed
extension's pack adds a cross-cutting layer — its own file, types and link types that may reach any layer — switched on per
workspace by a person, refused (never skipped) when the extension is missing or does not support this SDEM. Synthetic data only."""
import json, os, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from sdem import profile as P  # noqa: E402

PACK = {
    'format': 'sdem-profile/1', 'name': 'sectest', 'version': 1,
    'layers': [{'code': 'S', 'name': 'Security Architecture', 'position': 'across', 'file': 'security.json', 'description': 'controls and threats across A1–A4'}],
    'types': [{'type': 'SECT.S.SecurityControl', 'description': 'a measure that protects something', 'archimate': 'Requirement'},
              {'type': 'SECT.S.Threat', 'description': 'what could go wrong to what', 'archimate': 'Assessment'}],
    'attributes': [{'entity': 'SECT.S.SecurityControl', 'name': 'control_id', 'type': 'string', 'required': True}],
    'link_kinds': [{'kind': 'mitigates', 'source_type': 'SECT.S.SecurityControl', 'target_type': 'SECT.S.Threat', 'maps_to': 'association'}],
    'link_types': [{'source_type': 'SECT.S.SecurityControl', 'relationship': 'PROTECTS', 'target_type': 'A3.DataEntity', 'required_evidence': ['design_document']},
                   {'source_type': 'SECT.S.SecurityControl', 'relationship': 'PROTECTS', 'target_type': 'A1.BusinessProcess', 'required_evidence': ['design_document']}]}
CONTROLS = {'layer': 'S', 'reason': 'security design', 'changes': [
    {'op': 'add', 'record': {'id': 'CTL-SC28', 'type': 'SECT.S.SecurityControl', 'version': '1', 'name': 'Protection at rest', 'lifecycle_status': 'active', 'attributes': {'control_id': 'SC-28'}}},
    {'op': 'add', 'record': {'id': 'THR-DISCLOSE', 'type': 'SECT.S.Threat', 'version': '1', 'name': 'Payment data disclosed', 'lifecycle_status': 'active'}}],
    'relationships': {'add': [{'source': 'CTL-SC28', 'kind': 'mitigates', 'target': 'THR-DISCLOSE'}]}}


def fake_extension(folder, name, sdem_range='>=0.0'):
    """A stand-in for an installed metamodel extension: sdem-<name> answering --manifest with its pack."""
    pack = folder / f'{name}-pack.json'; pack.write_text(json.dumps(PACK))
    man = {'name': name, 'command': f'sdem-{name}', 'version': '0.1.0', 'kind': ['metamodel'], 'sdem': sdem_range, 'pack': str(pack), 'description': 'a test security pack'}
    body = f'import sys, json\nif "--manifest" in sys.argv: print(json.dumps({man!r}))\n'
    if os.name == 'nt':   # Windows finds a command by its extension (PATHEXT): a .cmd that runs the script with this Python
        (folder / f'sdem-{name}.py').write_text(body)
        (folder / f'sdem-{name}.cmd').write_text(f'@"{sys.executable}" "%~dp0sdem-{name}.py" %*\r\n')
    else:
        prog = folder / f'sdem-{name}'
        prog.write_text(f'#!{sys.executable}\n' + body)
        prog.chmod(0o755)


class MetamodelExtensionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = t = Path(tempfile.mkdtemp()); (t / 'bin').mkdir()
        fake_extension(t / 'bin', 'sectest'); fake_extension(t / 'bin', 'sectestold', sdem_range='<0.1')
        cls.env = {**os.environ, 'PYTHONPATH': str(ROOT) + os.pathsep + os.environ.get('PYTHONPATH', ''), 'PATH': str(t / 'bin') + os.pathsep + os.environ.get('PATH', '')}
        cls.ws = ws = t / 'ex'
        cls.sdem('new', '--workspace', ws, '--person', 'steven', '--example', 'payment-initiation')
        _, _, cls.included = cls.sdem('profile', 'include', 'ext:sectest', '--workspace', ws, '--person', 'steven', '--reason', 'security design', '--json')
        _, _, cls.adopted = cls.sdem('profile', 'adopt', '--workspace', ws, '--person', 'steven', '--reason', 'security layer', '--json')
        (t / 'sec.json').write_text(json.dumps(CONTROLS))
        cls.sdem('change', 'propose', t / 'sec.json', '--workspace', ws, '--agent', 'sdem-layer-s', '--person', 'steven')
        cls.sdem('connect', 'CTL-SC28', 'PROTECTS', 'ENT-PAY-INSTR', '--workspace', ws, '--person', 'steven', '--evidence', 'design_document:SEC-DESIGN#2', '--rationale', 'encrypted at rest')
        cls.sdem('connect', 'CTL-SC28', 'PROTECTS', 'PRC-PAY-01', '--workspace', ws, '--person', 'steven', '--evidence', 'design_document:SEC-DESIGN#1', '--rationale', 'the process handles the data')
        cls.sdem('build', '--workspace', ws, '--out', ws / 'graph')

    @classmethod
    def sdem(cls, *args, ok=(0,)):
        r = subprocess.run([sys.executable, '-m', 'sdem', *map(str, args)], cwd=cls.tmp, capture_output=True, text=True, env=cls.env)
        assert r.returncode in ok, f'sdem {" ".join(map(str, args))}: exit {r.returncode}\n{r.stdout[-1500:]}\n{r.stderr[-1500:]}'
        return r.returncode, r.stdout + r.stderr, (json.loads(r.stdout) if r.stdout.strip().startswith('{') else None)

    @classmethod
    def tearDownClass(cls): P.deactivate(); shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_a_person_switches_the_extension_on_and_its_layer_is_added(self):  # MX-10, LR-03
        self.assertEqual(self.included['kind'], 'metamodel extension'); self.assertIn('decision', self.included)
        self.assertEqual(self.adopted['layers_added'], ['security.json'])
        _, _, d = self.sdem('check', '--workspace', self.ws, '--require-recorded', '--json')
        self.assertTrue(d['ok'], d)

    def test_its_links_reach_layers_that_are_not_its_neighbour(self):  # LR-11, MX-05
        _, _, d = self.sdem('trace', 'CTL-SC28', '--graph', self.ws / 'graph', '--json')
        reached = json.dumps(d)
        self.assertIn('ENT-PAY-INSTR', reached); self.assertIn('PRC-PAY-01', reached)

    def test_impact_follows_them(self):  # MX-08
        _, out, d = self.sdem('impact', 'ENT-PAY-INSTR', '--change', 'retire', '--graph', self.ws / 'graph', '--json')
        self.assertIn('CTL-SC28', json.dumps(d))

    def test_its_rules_are_enforced(self):  # MX-04
        bad = json.loads(json.dumps(CONTROLS)); bad['changes'] = [{'op': 'add', 'record': {'id': 'CTL-X', 'type': 'SECT.S.SecurityControl', 'version': '1', 'name': 'No id', 'lifecycle_status': 'active'}}]
        bad['relationships'] = {'add': []}; (self.tmp / 'bad.json').write_text(json.dumps(bad))
        code, out, _ = self.sdem('change', 'propose', self.tmp / 'bad.json', '--workspace', self.ws, '--agent', 'sdem-layer-s', '--person', 'steven', '--dry-run', ok=(0, 1, 2, 3))
        self.assertNotEqual(code, 0); self.assertIn('control_id', out)

    def test_a_missing_or_unsupported_extension_is_refused_never_skipped(self):  # MX-11a
        prof = json.loads((self.ws / 'sdem-profile.json').read_text())
        for name, words in (('ext:notinstalled', 'not installed'), ('ext:sectestold', 'supports SDEM')):
            ws2 = self.tmp / name.replace(':', '-'); shutil.copytree(self.ws, ws2)
            (ws2 / 'sdem-profile.json').write_text(json.dumps({**prof, 'includes': [name]}))
            code, out, _ = self.sdem('check', '--workspace', ws2, ok=(1, 2, 3))
            self.assertIn(words, out)

    def test_a_published_copy_carries_the_pack_as_a_file(self):  # MX-01: where the extension is not installed (a site's own SDEM)
        ws2 = self.tmp / 'carried'; shutil.copytree(self.ws, ws2)
        shutil.copy(self.tmp / 'bin' / 'sectest-pack.json', ws2 / 'sectest-pack.json')
        prof = json.loads((ws2 / 'sdem-profile.json').read_text())
        prof['includes'] = ['sectest-pack.json' if i == 'ext:sectest' else i for i in prof.get('includes', [])]
        (ws2 / 'sdem-profile.json').write_text(json.dumps(prof))
        env = {k: v for k, v in self.env.items()}; env['PATH'] = os.environ.get('PATH', '')   # the extension is not on this PATH
        r = subprocess.run([sys.executable, '-m', 'sdem', 'check', '--workspace', ws2, '--json'], cwd=self.tmp, capture_output=True, text=True, env=env)
        self.assertEqual(r.returncode, 0, r.stdout[-800:] + r.stderr[-800:])

    def test_its_document_is_titled_by_the_layer_and_its_types(self):  # LR-01: a profile layer's document reads as the core's do
        _, out, _ = self.sdem('document', '--workspace', self.ws, '--layer', 'S')
        self.assertTrue(out.startswith('# S Security Architecture'), out[:80])
        self.assertIn('## 1. Security controls', out); self.assertNotIn('S.Security', out)

    def test_only_a_cross_cutting_layer_may_skip_layers(self):  # LR-06 still holds for above and below
        doc = json.loads(json.dumps(PACK)); doc['layers'][0]['position'] = 'below'
        f = self.tmp / 'below.json'; f.write_text(json.dumps(doc))
        from sdem.metamodel import Metamodel
        issues = P.check(P.resolve(f), Metamodel.base())
        self.assertTrue(any('directly below' in i for i in issues), issues)


if __name__ == '__main__':
    unittest.main()
