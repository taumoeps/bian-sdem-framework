"""The metamodel's health (docs/design/sdem-metamodel-stability.md, MS-01…MS-08): what is not yet settled, what workspaces use, the
core against its freeze, and what a BIAN release would affect. Synthetic data only."""
import json, os, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from sdem import model_health as H  # noqa: E402

ENV = {**os.environ, 'PYTHONPATH': str(ROOT) + os.pathsep + os.environ.get('PYTHONPATH', '')}


def sdem(*args, cwd, ok=(0,)):
    r = subprocess.run([sys.executable, '-m', 'sdem', *map(str, args)], cwd=cwd, capture_output=True, text=True, env=ENV)
    assert r.returncode in ok, f'sdem {" ".join(map(str, args))}: exit {r.returncode}\n{r.stdout[-900:]}\n{r.stderr[-900:]}'
    return r.returncode, r.stdout + r.stderr, (json.loads(r.stdout) if r.stdout.strip().startswith('{') else None)


class StatusTests(unittest.TestCase):
    def test_every_unsettled_item_has_a_source_and_a_way_to_settle_it(self):  # MS-01, MS-02
        r = H.status()
        self.assertEqual(r['summary']['cross-layer link type']['total'], 11)                                       # nine link types; DEPLOYED_ON has three target types (B1)
        self.assertEqual(len({i['id'].rsplit(' ', 1)[0] for i in r['items'] if i['area'] == 'cross-layer link type'}), 5)   # 5 of the 9 unsettled after B1
        links = {i['id']: i for i in r['items'] if i['area'] == 'cross-layer link type'}
        self.assertIn('A3.ApplicationComponent DEPLOYED_AS A4.Deployment', links)                                # an SDEM definition, not a standard's
        self.assertNotIn('A3.ApplicationComponent DEPLOYED_ON A4.SystemSoftware', links)                         # verified against ArchiMate 3.2 (B1)
        self.assertNotIn('A2.ServiceDomain REALIZED_BY A3.ApplicationComponent', links)                           # verified against BIAN's public guidance
        for i in r['items']: self.assertTrue(i['source'] and i['settle'] and all(i['settle']), i)
        self.assertIn('pending_release_validation', r['by_status'])

    def test_the_cli_reports_it(self):
        _, out, _ = sdem('model', 'status', '--area', 'cross-layer link type', cwd=ROOT)
        self.assertIn('cross-layer link type', out); self.assertIn('to settle:', out)


class StabilityTests(unittest.TestCase):
    def test_the_core_is_as_frozen(self):  # MS-04: CI fails if the core changed without an approved, versioned change and a freeze
        r = H.stability()
        self.assertEqual(r['issues'], [], 'the core of the metamodel changed — see docs/design/sdem-metamodel-stability.md')
        self.assertFalse(r['needs_freeze'], 'the core changed as the policy allows — record it: sdem model freeze --person <owner>')

    def test_a_change_needs_a_new_version_a_migration_and_deprecation_first(self):  # MS-05, MS-06
        now = H.snapshot(); frozen = json.loads(json.dumps(now))
        frozen['entity_types']['A9.Gone'] = 'active'                      # removed without deprecation
        frozen['attributes']['AT-OLD'] = 'deprecated'                     # removed after deprecation: allowed
        with mock.patch.object(H, '_j', side_effect=lambda p: frozen if Path(p) == H.STABILITY else json.loads(Path(p).read_text(encoding='utf-8'))):
            issues = ' | '.join(H.stability()['issues'])
        self.assertIn('metamodel_version is still', issues)
        self.assertIn('removed without being deprecated first', issues); self.assertIn('A9.Gone', issues); self.assertNotIn('AT-OLD', issues)


class UsageAndReleaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp()); cls.ws = cls.tmp / 'ws'
        sdem('new', '--workspace', cls.ws, '--person', 'steven', '--example', 'payment-initiation', cwd=cls.tmp)

    @classmethod
    def tearDownClass(cls): shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_usage_shows_what_is_used_and_what_no_workspace_uses(self):  # MS-03
        _, _, d = sdem('model', 'usage', '--workspace', self.ws, '--json', cwd=self.tmp)
        self.assertGreater(d['entity_types']['A3.ApplicationComponent'], 0)
        self.assertIn('A2.ServiceDomain REALIZED_BY A3.ApplicationComponent', d['link_types'])
        unused = [x['type'] for x in d['unused_core_types']]
        self.assertIn('A2.BusinessArea', unused); self.assertNotIn('A3.ApplicationComponent', unused)
        self.assertEqual(d['unused_core_types'][0]['unsettled'] != [], True)                          # the unsettled ones first

    def test_a_release_impact_lists_what_points_at_changed_records(self):  # MS-08
        a2 = json.loads((self.ws / 'a2-service-domain.json').read_text()); a2['model_version'] = 'synthetic-next'
        a2['instances'] = [i for i in a2['instances'] if i['id'] != 'SD-PA']
        next(i for i in a2['instances'] if i['id'] == 'SD-PI')['description'] = 'revised scope'
        (self.tmp / 'next.json').write_text(json.dumps(a2))
        before = (self.ws / 'a2-service-domain.json').read_bytes()
        _, _, d = sdem('bian', 'impact', '--workspace', self.ws, '--a2', self.tmp / 'next.json', '--json', cwd=self.tmp)
        r = {x['id']: x for x in d['workspaces'][0]['records']}
        self.assertEqual(r['SD-PI']['how'], ['changed']); self.assertIn('PAY-106 SD-PI -REALIZED_BY-> APP-PAY-HUB (approved)', r['SD-PI']['connections'])
        self.assertIn('not_in_release', r['SD-PA']['how'])
        self.assertEqual((self.ws / 'a2-service-domain.json').read_bytes(), before)                   # read-only


if __name__ == '__main__':
    unittest.main()
