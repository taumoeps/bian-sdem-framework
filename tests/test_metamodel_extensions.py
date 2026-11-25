"""Metamodel extensions (docs/design/sdem-metamodel-extensions-spec.md, MX-01…MX-11a; the layer registry's LR-11): an installed
extension's pack adds a cross-cutting layer — its own file, types and link types that may reach any layer — switched on per
workspace by a person, refused (never skipped) when the extension is missing or does not support this SDEM. Synthetic data only."""
import json, os, re, shutil, subprocess, sys, tempfile, unittest
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
    'link_types': [{'source_type': 'SECT.S.SecurityControl', 'relationship': 'PROTECTS', 'archimate': 'association', 'target_type': 'A3.DataEntity', 'required_evidence': ['design_document']},
                   {'source_type': 'SECT.S.SecurityControl', 'relationship': 'PROTECTS', 'archimate': 'association', 'target_type': 'A1.BusinessProcess', 'required_evidence': ['design_document']}],
    'computed_rules': [{'id': 'SECT-C01', 'message': 'a check the extension computes itself'}]}
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


import sys as _s, pathlib as _pl; _s.path.insert(0, str(_pl.Path(__file__).resolve().parent)); from needs import bian as _needs_bian  # noqa: E402 — BX-15: tests that need sdem-bian

@_needs_bian
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

    def test_a_person_may_grant_an_exception_to_a_rule_the_extension_computes(self):  # MX-17
        _, out, _ = self.sdem('exception', 'grant', '--workspace', self.ws, '--rule', 'SECT-C01', '--records', 'APP-PAY-HUB', '--expires', '2099-12-31',
                              '--reason', 'made-up', '--person', 'steven', '--dry-run', ok=(0, 1, 2))
        self.assertNotIn('not a rule of the profile', out)

    def test_switching_it_off_archives_its_layer_and_never_reuses_a_link_id(self):  # MX-16
        ws = self.tmp / 'off'; shutil.copytree(self.ws, ws)
        maps = json.loads((ws / 'mappings.json').read_text())['mappings']
        ours = [m['mapping_id'] for m in maps if m['source']['id'] == 'CTL-SC28']
        _, _, d = self.sdem('profile', 'exclude', 'ext:sectest', '--workspace', ws, '--person', 'steven', '--reason', 'made-up', '--json')
        self.assertEqual(sorted(d['connections_retired']), sorted(ours)); self.assertFalse((ws / 'security.json').exists())
        arc = json.loads((ws / d['archive']).read_text()); self.assertIn('security.json', arc['files']); self.assertEqual(len(arc['mappings']), len(ours))
        _, _, c = self.sdem('check', '--workspace', ws, '--require-recorded', '--json'); self.assertTrue(c['ok'], c)
        _, _, n = self.sdem('connect', 'PRC-PAY-02', 'USES_DOMAIN', 'SD-PA', '--workspace', ws, '--person', 'steven', '--evidence', 'business_architecture_document:made-up#1',
                            '--evidence', 'domain_scope_assessment:made-up#1', '--evidence', 'process_model:made-up#1', '--rationale', 'made-up', '--json', ok=(0, 1, 2))
        self.assertIsNotNone(n, 'the new connection was not made')
        new = {m['mapping_id'] for m in json.loads((ws / 'mappings.json').read_text())['mappings']} - {m['mapping_id'] for m in maps}
        num = lambda i: int(re.search(r'(\d+)$', i).group(1))
        self.assertEqual(len(new), 1); self.assertGreater(num(new.pop()), max(num(i) for i in ours), 'a new link took a retired id')   # the security links were the newest

    def test_switching_off_twice_in_a_day_keeps_both_archives(self):  # MX-16, AUD-24
        ws = self.tmp / 'twice'; shutil.copytree(self.ws, ws)
        _, _, d1 = self.sdem('profile', 'exclude', 'ext:sectest', '--workspace', ws, '--person', 'steven', '--reason', 'one', '--json')
        self.sdem('profile', 'include', 'ext:sectest', '--workspace', ws, '--person', 'steven', '--reason', 'again')
        self.sdem('profile', 'adopt', '--workspace', ws, '--person', 'steven', '--reason', 'again')
        _, _, d2 = self.sdem('profile', 'exclude', 'ext:sectest', '--workspace', ws, '--person', 'steven', '--reason', 'two', '--json')
        self.assertNotEqual(d1['archive'], d2['archive'])
        first = json.loads((ws / d1['archive']).read_text()); self.assertEqual(len(first['mappings']), len(d1['connections_retired']))
        self.assertTrue(d1['connections_retired'])

    def test_restore_brings_it_back_with_its_old_ids_and_purge_deletes_only_the_archive(self):  # EL-06, EL-16
        ws = self.tmp / 'back'; shutil.copytree(self.ws, ws)
        before = sorted(m['mapping_id'] for m in json.loads((ws / 'mappings.json').read_text())['mappings'])
        _, _, d = self.sdem('profile', 'exclude', 'ext:sectest', '--workspace', ws, '--person', 'steven', '--reason', 'off', '--json')
        _, _, r = self.sdem('profile', 'restore', '--archive', d['archive'], '--workspace', ws, '--person', 'steven', '--reason', 'on again', '--json')
        self.assertEqual(sorted(r['connections']), sorted(d['connections_retired']))
        self.assertEqual(sorted(m['mapping_id'] for m in json.loads((ws / 'mappings.json').read_text())['mappings']), before)   # the same links, the same ids
        self.assertIn('ext:sectest', json.loads((ws / 'sdem-profile.json').read_text())['includes'])
        _, _, c = self.sdem('check', '--workspace', ws, '--require-recorded', '--json'); self.assertTrue(c['ok'], c)
        code, out, _ = self.sdem('profile', 'restore', '--archive', d['archive'], '--workspace', ws, '--person', 'steven', '--reason', 'twice', ok=(1, 2))
        self.assertIn('already restored', out)
        _, _, d2 = self.sdem('profile', 'exclude', 'ext:sectest', '--workspace', ws, '--person', 'steven', '--reason', 'off for good', '--json')
        _, _, dry = self.sdem('profile', 'purge', 'ext:sectest', '--workspace', ws, '--person', 'steven', '--reason', 'a data request', '--dry-run', '--json')
        self.assertEqual(len(dry['purged']), 2); self.assertTrue((ws / d2['archive']).exists())
        _, _, pg = self.sdem('profile', 'purge', 'ext:sectest', '--workspace', ws, '--person', 'steven', '--reason', 'a data request', '--json')
        self.assertFalse((ws / d['archive']).exists()); self.assertFalse((ws / d2['archive']).exists())
        ret = json.loads((ws / 'archive' / 'retired-mappings.json').read_text())['mappings']
        self.assertEqual(sorted(m['mapping_id'] for m in ret), sorted(d2['connections_retired']))   # still retired, never given again
        self.assertTrue(all(m['archive'] is None and m['purged'] == pg['decision'] for m in ret))
        gd = json.loads(next((ws / 'decisions').glob(f"{pg['decision']}.json")).read_text())
        self.assertNotIn('CTL-SC28', json.dumps(gd))   # the decision records what was deleted, not its content

    def test_only_a_cross_cutting_layer_may_skip_layers(self):  # LR-06 still holds for above and below
        doc = json.loads(json.dumps(PACK)); doc['layers'][0]['position'] = 'below'
        f = self.tmp / 'below.json'; f.write_text(json.dumps(doc))
        from sdem.metamodel import Metamodel
        issues = P.check(P.resolve(f), Metamodel.base())
        self.assertTrue(any('directly below' in i for i in issues), issues)


if __name__ == '__main__':
    unittest.main()


class ExtensionRequiresAnother(unittest.TestCase):   # MID-10: an extension may require another — kept where it is on, else left out and said
    def merged(self, includes):
        t = Path(tempfile.mkdtemp()); self.addCleanup(shutil.rmtree, t, True)
        net = {'format': 'sdem-profile/1', 'name': 'networks', 'version': 1,
               'types': [{'type': 'NET.A4.Firewall', 'extends': ['A4.Node'], 'description': 'a firewall (made-up)', 'archimate': 'Node'}]}
        dr = {'format': 'sdem-profile/1', 'name': 'recovery', 'version': 1,
              'types': [{'type': 'DRX.A4.ReplicaGroup', 'extends': ['A4.Node'], 'description': 'a recovery group (made-up)', 'archimate': 'Node'},
                        {'type': 'DRX.A4.FailoverGate', 'extends': ['A4.Node'], 'description': 'needs the networks extension', 'archimate': 'Node', 'requires': 'file:net.json'}]}
        (t / 'net.json').write_text(json.dumps(net)); (t / 'dr.json').write_text(json.dumps(dr))
        (t / 'profile.json').write_text(json.dumps({'format': 'sdem-profile/1', 'name': 'team', 'version': 1, 'includes': includes}))
        return P.resolve(t / 'profile.json')

    def test_kept_where_the_other_is_on(self):
        m = self.merged(['net.json', 'dr.json'])
        self.assertIn('DRX.A4.FailoverGate', {x['type'] for x in m['types']})

    def test_left_out_and_said_where_it_is_not(self):
        m = self.merged(['dr.json'])
        types = {x['type'] for x in m['types']}
        self.assertIn('DRX.A4.ReplicaGroup', types); self.assertNotIn('DRX.A4.FailoverGate', types)       # the rest of the extension stays
        self.assertIn({'extension': 'recovery', 'type': 'DRX.A4.FailoverGate', 'requires': 'file:net.json'},
                      [{k: x.get(k) for k in ('extension', 'type', 'requires')} for x in m.get('left_out', [])])
