"""`sdem diagram` (docs/design/sdem-diagram-spec.md, DG-01…DG-14): SDEM's ArchiMate templates on any workspace — only records and
stored, approved links drawn; gaps said; deterministic; the templates checked against the metamodel; focus; the workbench carries them."""
import json, os, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
ENV = {**os.environ, 'PYTHONPATH': str(ROOT) + os.pathsep + os.environ.get('PYTHONPATH', '')}
sys.path.insert(0, str(ROOT))
from sdem import viewpoints as vp

EXAMPLES = sorted(p for p in (ROOT / 'examples').iterdir() if (p / 'mappings.json').exists())
IDS = [t['id'] for t in vp.templates()['templates']]


def sdem(*args, cwd=ROOT):
    r = subprocess.run([sys.executable, '-m', 'sdem', *map(str, args)], cwd=cwd, capture_output=True, text=True, env=ENV)
    return r.returncode, r.stdout, r.stderr


class TemplateTests(unittest.TestCase):
    def test_the_templates_match_the_metamodel(self):                                    # DG-02
        self.assertEqual(vp.check(), [])
        self.assertEqual(set(IDS), {'capabilities', 'process', 'bian', 'application', 'technology', 'layered'})

    def test_the_check_catches_a_type_the_metamodel_does_not_have(self):
        tf = vp.templates(); tf['templates'][0]['rows'][0]['groups'][0]['type'] = 'A1.NoSuchType'
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'v.json'; p.write_text(json.dumps(tf), encoding='utf-8')
            with mock.patch.object(vp, 'TEMPLATES_FILE', p):
                self.assertTrue(any('A1.NoSuchType' in b for b in vp.check()))

    def test_templates_name_no_workspace(self):                                         # DG-01
        text = vp.TEMPLATES_FILE.read_text(encoding='utf-8')
        for word in ('PAY-', 'APP-', 'SD-PI', 'payment-initiation'):
            self.assertNotIn(word, text)


class DrawingTests(unittest.TestCase):
    def test_every_template_on_every_example_draws_only_what_is_stored(self):           # DG-03 on any workspace
        for ws in EXAMPLES:
            D = vp.Data(ws)
            approved = {m['mapping_id'] for m in D.maps}
            kinds = set(vp.templates()['notation']['kinds'])
            for t in IDS:
                with self.subTest(ws=ws.name, template=t):
                    d = vp.build(D, t)
                    self.assertTrue(all(i in D.rec for i in d['elements']))
                    for line in d['lines']:
                        self.assertTrue(line['stands_for'])
                        self.assertTrue(all(r in approved or r in kinds for r in line['stands_for']), line)
                    self.assertNotIn('href="http', d['svg']); self.assertNotIn('<script', d['svg'])   # DG-06

    def test_deterministic(self):                                                        # DG-05
        ws = ROOT / 'examples' / 'payment-initiation'
        self.assertEqual(vp.build(vp.Data(ws), 'layered')['svg'], vp.build(vp.Data(ws), 'layered')['svg'])

    def test_rolled_up_lines_say_how_many_links(self):                                   # DG-09
        d = vp.build(vp.Data(ROOT / 'examples' / 'payment-initiation'), 'layered')
        impl = [x for x in d['lines'] if x['source'] == 'SD-PI' and x['target'] == 'IFC-PAY-API']
        self.assertEqual(len(impl), 1); self.assertEqual(len(impl[0]['stands_for']), 5); self.assertIn('×5', impl[0]['label'])

    def test_gaps_are_said(self):                                                        # DG-04
        d = vp.build(vp.Data(ROOT / 'examples' / 'payment-initiation'), 'process')
        self.assertTrue(any('No sequence is recorded' in n for n in d['notes']))
        d = vp.build(vp.Data(ROOT / 'examples' / 'digital-lending'), 'layered')
        self.assertTrue(any('no A3 dataset' in n for n in d['notes'])); self.assertIn('A3', d['missing_layers'])

    def test_focus(self):                                                                # DG-08
        D = vp.Data(ROOT / 'examples' / 'payment-initiation')
        d = vp.build(D, 'process', focus='PRC-PAY-01')
        self.assertIn('PRC-PAY-01', d['elements']); self.assertIn('ACT-PAY-01a', d['elements']); self.assertIn('SD-PI', d['elements'])
        self.assertNotIn('PRC-PAY-02', d['elements'])
        with self.assertRaises(ValueError): vp.build(D, 'process', focus='NOPE')


class CommandTests(unittest.TestCase):
    def test_cli(self):                                                                  # DG-14
        code, out, err = sdem('diagram', '--list', '--json'); self.assertEqual(code, 0, err)
        self.assertEqual([r['id'] for r in json.loads(out)['items']], IDS)   # SDEM's JSON envelope
        self.assertEqual(sdem('diagram', '--check')[0], 0)
        with tempfile.TemporaryDirectory() as d:
            for fmt in ('svg', 'html', 'json'):
                code, out, err = sdem('diagram', '--workspace', 'examples/payment-initiation', '--template', 'application', '-o', f'{d}/a.{fmt}')
                self.assertEqual(code, 0, err)
            self.assertTrue((Path(d) / 'a.svg').read_text(encoding='utf-8').startswith('<svg'))
            self.assertIn('sdemDiagrams', (Path(d) / 'a.html').read_text(encoding='utf-8'))
            self.assertEqual(json.loads((Path(d) / 'a.json').read_text(encoding='utf-8'))['template'], 'application')
            self.assertEqual(sdem('diagram', '--workspace', 'examples/payment-initiation', '--template', 'nope')[0], 2)
            (Path(d) / 'empty').mkdir()
            self.assertEqual(sdem('diagram', '--workspace', f'{d}/empty')[0], 2)

    def test_an_empty_workspace_draws_and_says_so(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(sdem('new', '--workspace', 'e', '--person', 'jane.architect', cwd=d)[0], 0)
            out = vp.build(vp.Data(Path(d) / 'e'), 'layered')
            self.assertEqual(out['elements'], []); self.assertTrue(any('Nothing to draw' in n for n in out['notes']))

    def test_the_workbench_carries_each_layers_diagrams(self):                            # DG-13
        from sdem import workbench
        with tempfile.TemporaryDirectory() as d:
            ws = Path(d) / 'ws'; shutil.copytree(ROOT / 'examples' / 'payment-initiation', ws, ignore=shutil.ignore_patterns('graph', 'migrations'))
            data = workbench.collect(ws)
            self.assertEqual(set(data['diagrams']), set(IDS))
            self.assertEqual({x['layer'] for x in data['diagrams'].values()}, {'A1', 'A2', 'A3', 'A4', 'all'})
            self.assertIn('sdemDiagrams', workbench.render(data))
            page = workbench.render(data)
            self.assertIn("function overview(){const L=(D.diagrams||{}).layered;", page)   # the layered view is on the Overview
            self.assertNotIn('Layered view (ArchiMate)</option>', page)                    # not in the Knowledge Graphs scope
            self.assertIn('data-fit=', page)                                               # fit to width / actual size


if __name__ == '__main__':
    unittest.main()
