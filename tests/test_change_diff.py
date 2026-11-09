"""Structured reconciliation (owner's decision D5, 2026-11-09; AG-K08, AG-K09 in docs/design/sdem-agent-platform-spec.md): an incoming
layer file is compared with the workspace and becomes a change set — nothing applied, nothing removed because it was left out; an update
merges; a link is its ends and kind, its citation describes it."""
import copy, json, os, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from sdem.agents import CoordinationError, Estate, merge_record  # noqa: E402
from sdem.validate import check_schema  # noqa: E402

ENV = {**os.environ, 'PYTHONPATH': str(ROOT) + os.pathsep + os.environ.get('PYTHONPATH', '')}
AGENT, PERSON = 'sdem-a3-application', 'jane.architect'


def _j(p): return json.loads(Path(p).read_text(encoding='utf-8'))


class DiffTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()); self.ws = self.tmp / 'ws'
        shutil.copytree(ROOT / 'examples' / 'payment-initiation', self.ws, ignore=shutil.ignore_patterns('graph', 'migrations', 'm1-*'))
        self.est = Estate(self.ws); self.a3 = _j(self.ws / 'a3-application.json')
        self.op = next(i for i in self.a3['instances'] if i['id'] == 'API-PI-01')

    def tearDown(self): shutil.rmtree(self.tmp, ignore_errors=True)

    def incoming(self, instances, rels=()):
        return {'level': 'A3', 'model_id': 'drafted', 'instances': instances, 'relationships': list(rels)}

    def test_a_partial_file_changes_only_what_it_says(self):
        part = {**{k: self.op[k] for k in ('id', 'type', 'version', 'name')}, 'attributes': {'path': '/v2/payment-instructions'}}
        r = self.est.compare(self.incoming([part]))
        self.assertEqual(r['summary']['update'], 1); self.assertEqual(r['retire_candidates'], [])
        upd = r['changes'][0]
        self.assertEqual(upd['fields_changed'], ['attributes.path']); self.assertEqual(upd['record']['attributes'], {'path': '/v2/payment-instructions'})
        self.assertEqual(_j(self.ws / 'a3-application.json'), self.a3, 'compare writes nothing')

    def test_the_change_set_is_valid_applies_by_merging_and_a_second_diff_is_empty(self):   # idempotent
        part = {**{k: self.op[k] for k in ('id', 'type', 'version', 'name')}, 'attributes': {'path': '/v2/payment-instructions'}}
        r = self.est.compare(self.incoming([part]))
        schema = json.loads((ROOT / 'schema' / 'coordination.schema.json').read_text())
        self.assertEqual(check_schema(r['change_set'], schema['$defs']['change_set_input'], schema), [])
        self.est.propose(r['change_set'], AGENT, PERSON)
        after = next(i for i in _j(self.ws / 'a3-application.json')['instances'] if i['id'] == 'API-PI-01')
        self.assertEqual(after['attributes']['path'], '/v2/payment-instructions')
        self.assertEqual(after['attributes']['method'], self.op['attributes']['method'])   # kept: not in the partial record
        again = self.est.compare(self.incoming([part]))
        self.assertEqual((again['summary']['add'], again['summary']['update'], again['summary']['unchanged']), (0, 0, 1))

    def test_a_complete_snapshot_lists_retirement_candidates_but_never_retires(self):
        keep = [i for i in self.a3['instances'] if i['id'] != 'API-PI-01']
        rels = [x for x in self.a3['relationships'] if 'API-PI-01' not in (x['source'], x['target'])]
        r = self.est.compare(self.incoming(copy.deepcopy(keep), rels), complete=True)
        self.assertIn('API-PI-01', r['retire_candidates'])
        self.assertFalse([c for c in r['change_set']['changes'] if c['op'] in ('retire', 'remove')])
        self.assertTrue(any(x['target'] == 'API-PI-01' for x in r['relationships']['remove']))

    def test_complete_compares_field_by_field_and_removes_an_attribute_left_out(self):
        full = copy.deepcopy(self.op); full['attributes'].pop('operation_id')
        r = self.est.compare(self.incoming([full]), complete=True)
        upd = next(c for c in r['changes'] if c['record']['id'] == 'API-PI-01')
        self.assertEqual(upd['record']['attributes'], {'operation_id': None})
        self.est.propose({**r['change_set'], 'relationships': {'add': [], 'remove': []}}, AGENT, PERSON)
        after = next(i for i in _j(self.ws / 'a3-application.json')['instances'] if i['id'] == 'API-PI-01')
        self.assertNotIn('operation_id', after['attributes'])

    def test_conflicts(self):
        other_layer = next(i['id'] for i in _j(self.ws / 'a4-technology.json')['instances'])
        r = self.est.compare(self.incoming([
            {**self.op, 'type': 'A3.ApplicationService'},                                                        # type change
            {'id': other_layer, 'type': 'A3.ApplicationComponent', 'version': '1', 'name': 'x'},                   # id used in A4
            {'id': 'CMP-X', 'type': 'A4.Node', 'version': '1', 'name': 'x'}],                                      # not an A3 type
            [{'source': 'API-PI-01', 'kind': 'composition', 'target': 'NOWHERE'}]))
        reasons = ' | '.join(c['reason'] for c in r['conflicts'])
        for want in ('type changes from', 'already used in A4', 'not a A3 type', 'not in this layer'): self.assertIn(want, reasons)
        self.assertFalse(r['change_set']['changes'])
        with self.assertRaises(CoordinationError): self.est.compare({'instances': []})

    def test_a_record_with_an_existing_natural_key_is_a_possible_duplicate_not_an_add(self):
        hub = next(i for i in self.a3['instances'] if i['type'] == 'A3.ApplicationComponent')
        r = self.est.compare(self.incoming([{'id': 'CMP-NEW', 'type': hub['type'], 'version': '1', 'name': '  ' + hub['name'].lower() + '.'}]))
        self.assertEqual(r['possible_duplicates'][0]['existing'], hub['id']); self.assertEqual(r['summary']['add'], 0)

    def test_a_link_is_its_ends_and_kind_and_its_citation_is_kept(self):
        rel = dict(self.a3['relationships'][0]); cited = {**rel, 'source_id': 'document:DESIGN.md#4.2'}
        r = self.est.compare(self.incoming([], [cited]))
        self.assertEqual(r['relationships']['add'], [cited])
        self.est.propose({'layer': 'A3', 'reason': 'cite', 'changes': [], 'relationships': {'add': [cited], 'remove': []}}, AGENT, PERSON)
        rels = _j(self.ws / 'a3-application.json')['relationships']
        same = [x for x in rels if (x['source'], x['kind'], x['target']) == (rel['source'], rel['kind'], rel['target'])]
        self.assertEqual(len(same), 1); self.assertEqual(same[0]['source_id'], 'document:DESIGN.md#4.2')

    def test_the_command(self):
        part = {**{k: self.op[k] for k in ('id', 'type', 'version', 'name')}, 'attributes': {'path': '/v3'}}
        (self.tmp / 'in.json').write_text(json.dumps(self.incoming([part])))
        out = subprocess.run([sys.executable, '-m', 'sdem', 'change', 'diff', str(self.tmp / 'in.json'), '--workspace', str(self.ws), '-o', str(self.tmp / 'cs.json'), '--json'],
                             capture_output=True, text=True, env=ENV, cwd=self.tmp)
        self.assertEqual(out.returncode, 0, out.stderr); self.assertEqual(json.loads(out.stdout)['summary']['update'], 1)
        self.assertEqual(_j(self.tmp / 'cs.json')['changes'][0]['op'], 'update')


class MergeTests(unittest.TestCase):
    def test_merge_sets_keeps_and_removes(self):
        old = {'id': 'X', 'type': 'A3.APIOperation', 'version': '1', 'name': 'a', 'description': 'd', 'attributes': {'method': 'GET', 'path': '/a', 'deprecated': False}}
        new = merge_record(old, {'id': 'X', 'type': 'A3.APIOperation', 'version': '2', 'name': 'a', 'description': None, 'attributes': {'path': '/b', 'deprecated': None}})
        self.assertEqual(new, {'id': 'X', 'type': 'A3.APIOperation', 'version': '2', 'name': 'a', 'attributes': {'method': 'GET', 'path': '/b'}})
        self.assertEqual(old['attributes']['path'], '/a')


if __name__ == '__main__':
    unittest.main()
