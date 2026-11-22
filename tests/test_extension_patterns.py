"""MIP-10, MID-08 (docs/design/metamodel-integrity-design.md §3a): extensions are handled by pattern, not by name. Three made-up
extensions — one of each pattern — are switched on, given records, linked, checked and traced with no SDEM code written for them:
H1 *Facilities* (a layer below the stack), H2 *Networks* (a kind of Technology node), V1 *Disaster Recovery* (a layer beside the stack).
Synthetic data only."""
import json, os, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from sdem import profile as P  # noqa: E402

PACKS = {
    'facilities': {'format': 'sdem-profile/1', 'name': 'facilities', 'version': 1,   # H1: a layer in the stack, below Technology
                 'layers': [{'code': 'P', 'name': 'Facilities Architecture', 'position': 'below', 'file': 'facilities.json', 'description': 'sites and racks (made-up)'}],
                 'types': [{'type': 'PHY.P.Site', 'description': 'a data centre site (made-up)', 'archimate': 'Location'}],
                 'link_types': [{'source_type': 'A4.Node', 'relationship': 'LOCATED_AT', 'target_type': 'PHY.P.Site', 'required_evidence': ['design_document']}]},
    'networks': {'format': 'sdem-profile/1', 'name': 'networks', 'version': 1,   # H2: a kind of record inside Technology
                 'types': [{'type': 'NET.A4.Firewall', 'extends': 'A4.Node', 'description': 'a firewall (made-up)', 'archimate': 'Node'}]},
    'recovery': {'format': 'sdem-profile/1', 'name': 'recovery', 'version': 1,   # V1: a layer beside the stack
                 'layers': [{'code': 'D', 'name': 'Disaster Recovery', 'position': 'across', 'file': 'recovery.json', 'description': 'recovery plans (made-up)'}],
                 'types': [{'type': 'DRX.D.RecoveryPlan', 'description': 'how something is recovered (made-up)', 'archimate': 'CourseOfAction'}],
                 'link_types': [{'source_type': 'DRX.D.RecoveryPlan', 'relationship': 'RECOVERS', 'target_type': 'A3.DataEntity', 'required_evidence': ['design_document']}]},
}


def fake_extension(folder, name):
    """A stand-in for an installed metamodel extension: sdem-<name> answering --manifest with its pack."""
    pack = folder / f'{name}-pack.json'; pack.write_text(json.dumps(PACKS[name]))
    man = {'name': name, 'command': f'sdem-{name}', 'version': '0.1.0', 'kind': ['metamodel'], 'sdem': '>=0.0', 'pack': str(pack), 'description': f'a made-up {name} pack'}
    body = f'import sys, json\nif "--manifest" in sys.argv: print(json.dumps({man!r}))\n'
    if os.name == 'nt':
        (folder / f'sdem-{name}.py').write_text(body)
        (folder / f'sdem-{name}.cmd').write_text(f'@"{sys.executable}" "%~dp0sdem-{name}.py" %*\r\n')
    else:
        prog = folder / f'sdem-{name}'; prog.write_text(f'#!{sys.executable}\n' + body); prog.chmod(0o755)


def ids(tree):
    out = set()
    def walk(n): out.add(n['id']); [walk(c['node']) for c in n.get('children') or []]
    walk(tree); return out


class ExtensionsByPattern(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = t = Path(tempfile.mkdtemp()); (t / 'bin').mkdir()
        for n in PACKS: fake_extension(t / 'bin', n)
        cls.env = {**os.environ, 'PYTHONPATH': str(ROOT), 'PYTHONIOENCODING': 'utf-8', 'PATH': str(t / 'bin') + os.pathsep + os.environ.get('PATH', '')}
        cls.ws = ws = t / 'ws'
        cls.sdem('new', '--workspace', ws, '--person', 'steven', '--example', 'payment-initiation')
        for n in PACKS: cls.sdem('profile', 'include', f'ext:{n}', '--workspace', ws, '--person', 'steven', '--reason', f'{n} (made-up)')
        cls.sdem('profile', 'adopt', '--workspace', ws, '--person', 'steven', '--reason', 'three made-up extensions')
        cls.layers = json.loads(cls.sdem('layers', '--workspace', ws, '--json')[1]) if cls.sdem('layers', '--workspace', ws, '--json', ok=(0, 1, 2))[0] == 0 else None
        node = cls.first(ws / 'technology.json', 'technology.Node')
        cls.node, cls.entity = node, cls.first(ws / 'data.json', 'data.DataEntity')
        cls.change({'layer': 'technology', 'reason': 'a firewall (made-up)', 'changes': [
            {'op': 'add', 'record': {'id': 'FW-EDGE', 'type': 'NET.A4.Firewall', 'version': '1', 'name': 'Edge firewall', 'lifecycle_status': 'planned'}}],
            'relationships': {'add': [{'source': 'FW-EDGE', 'kind': 'assignment', 'target': cls.first(ws / 'technology.json', 'technology.SystemSoftware')}]}}, 'fw')
        cls.change({'layer': 'P', 'reason': 'a site (made-up)', 'changes': [
            {'op': 'add', 'record': {'id': 'SITE-1', 'type': 'PHY.P.Site', 'version': '1', 'name': 'Site one', 'lifecycle_status': 'planned'}}]}, 'site')
        cls.change({'layer': 'D', 'reason': 'a recovery plan (made-up)', 'changes': [
            {'op': 'add', 'record': {'id': 'DRP-PAY', 'type': 'DRX.D.RecoveryPlan', 'version': '1', 'name': 'Payment data recovery', 'lifecycle_status': 'planned'}}]}, 'drp')
        cls.sdem('connect', node, 'LOCATED_AT', 'SITE-1', '--workspace', ws, '--person', 'steven', '--evidence', 'design_document:made-up#1', '--rationale', 'hosted there')
        cls.sdem('connect', 'DRP-PAY', 'RECOVERS', cls.entity, '--workspace', ws, '--person', 'steven', '--evidence', 'design_document:made-up#2', '--rationale', 'restored from replica')
        cls.g = ws / 'graph'; cls.sdem('build', '--workspace', ws, '--out', cls.g)

    @classmethod
    def first(cls, f, t):
        return next(r['id'] for r in json.loads(Path(f).read_text(encoding='utf-8'))['instances'] if r['type'] == t)

    @classmethod
    def change(cls, cs, name):
        f = cls.tmp / f'{name}.json'; f.write_text(json.dumps(cs))
        cls.sdem('change', 'propose', f, '--workspace', cls.ws, '--agent', {'technology': 'sdem-a4-technology'}.get(cs['layer'], f'sdem-layer-{cs["layer"].lower()}'), '--person', 'steven')

    @classmethod
    def sdem(cls, *args, ok=(0,)):
        r = subprocess.run([sys.executable, '-m', 'sdem', *map(str, args)], cwd=cls.tmp, capture_output=True, text=True, encoding='utf-8', env=cls.env)
        assert r.returncode in ok, f'sdem {" ".join(map(str, args))}: exit {r.returncode}\n{r.stdout[-1500:]}\n{r.stderr[-1500:]}'
        return r.returncode, r.stdout

    @classmethod
    def tearDownClass(cls): P.deactivate(); shutil.rmtree(cls.tmp, ignore_errors=True)

    def trace(self, rid, d):
        return ids(json.loads(self.sdem('trace', rid, '--graph', self.g, '--direction', d, '--json')[1])[d])

    def test_the_design_passes_with_all_three_on(self):
        self.assertIn('OK', self.sdem('check', '--workspace', self.ws)[1])

    def test_h1_a_layer_below_the_stack_is_traced(self):   # Facilities: a node reaches its site
        self.assertIn('SITE-1', self.trace(self.node, 'down'))

    def test_h2_a_kind_of_node_is_counted_and_traced_as_a_node(self):   # Networks: the firewall is a node to every rule and trace
        self.assertGreater(len(self.trace('FW-EDGE', 'down')), 1)

    def test_v1_a_layer_beside_the_stack_is_traced_through_what_it_links_to(self):   # Disaster Recovery: FT-09 for any across layer
        self.assertIn(self.entity, self.trace('DRP-PAY', 'down'))

    def test_no_sdem_code_names_them(self):
        code = ''.join(p.read_text(encoding='utf-8') for p in (ROOT / 'sdem').rglob('*.py'))
        for word in ('PHY.', 'NET.', 'DRX.', "'networks'", "'recovery'"):
            self.assertNotIn(word, code)


if __name__ == '__main__':
    unittest.main()
