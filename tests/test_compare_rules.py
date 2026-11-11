"""A `compare` rule (PR-11) never reports compliant when it could not compare (PR-11a): a value that is missing or a placeholder,
on either record, or a linked record that is not in the workspace, is unresolved — synthetic records only."""
import sys, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from sdem.comply import evaluate  # noqa: E402
from sdem.metamodel import Metamodel  # noqa: E402

MM = Metamodel.load()
DIFFER = {'id': 'R-DR', 'entity': 'A4.InfrastructureComponent', 'compare': {'kind': 'dr_pair_of', 'attribute': 'dr_region', 'must': 'differ'}}
SHARE = {**DIFFER, 'id': 'R-SAME', 'compare': {**DIFFER['compare'], 'must': 'equal'}}


def outcome(mine, theirs, rule=DIFFER, target='P2', extra=None):
    a = {} if mine is None else {'dr_region': mine}
    b = {} if theirs is None else {'dr_region': theirs}
    inst = [{'id': 'P1', 'type': 'A4.InfrastructureComponent', 'name': 'Platform one', 'attributes': {**a, **(extra or {})}},
            {'id': 'P2', 'type': 'A4.InfrastructureComponent', 'name': 'Platform two', 'attributes': b}]
    ds = {'A4': {'level': 'A4', 'instances': inst, 'relationships': [{'source': 'P1', 'kind': 'dr_pair_of', 'target': target}]}}
    f = next(x for x in evaluate(ds, [], MM, [rule]) if x['record'] == 'P1')
    return f['outcome'], f.get('detail', '')


class CompareRuleTests(unittest.TestCase):
    def test_values_that_compare(self):                                  # PR-11
        self.assertEqual(outcome('east', 'west')[0], 'compliant')
        self.assertEqual(outcome('east', 'east')[0], 'non_compliant')
        self.assertEqual(outcome('east', 'east', SHARE)[0], 'compliant')
        self.assertEqual(outcome('east', 'west', SHARE)[0], 'non_compliant')

    def test_a_missing_value_is_unresolved_never_compliant(self):        # PR-11a (was compliant)
        for mine, theirs, who in ((None, 'west', 'P1'), ('east', None, 'P2'), (None, None, 'P1 and P2')):
            got, why = outcome(mine, theirs)
            self.assertEqual(got, 'unresolved', (mine, theirs)); self.assertIn(f'dr_region of {who} not known', why)
            self.assertEqual(outcome(mine, theirs, SHARE)[0], 'unresolved')

    def test_a_placeholder_is_not_a_value(self):                         # PR-11a with PR-20 (TBD vs TBD was non_compliant; TBD vs west compliant)
        for mine, theirs in (('TBD', 'TBD'), ('TBD', 'west'), ('east', 'unknown'), ('', 'west')):
            self.assertEqual(outcome(mine, theirs)[0], 'unresolved', (mine, theirs))

    def test_a_pair_not_in_the_workspace_is_unresolved(self):            # PR-11a (was compliant)
        got, why = outcome('east', 'west', target='P9')
        self.assertEqual(got, 'unresolved'); self.assertIn('P9 (dr_pair_of) is not in the workspace', why)

    def test_a_real_difference_still_fails_beside_an_unknown_one(self):  # a known breach is not hidden by an unknown
        inst = [{'id': 'P1', 'type': 'A4.InfrastructureComponent', 'name': 'One', 'attributes': {'dr_region': 'east'}},
                {'id': 'P2', 'type': 'A4.InfrastructureComponent', 'name': 'Two', 'attributes': {'dr_region': 'east'}},
                {'id': 'P3', 'type': 'A4.InfrastructureComponent', 'name': 'Three', 'attributes': {}}]
        rels = [{'source': 'P1', 'kind': 'dr_pair_of', 'target': t} for t in ('P2', 'P3')]
        f = next(x for x in evaluate({'A4': {'level': 'A4', 'instances': inst, 'relationships': rels}}, [], MM, [DIFFER]) if x['record'] == 'P1')
        self.assertEqual(f['outcome'], 'non_compliant')

    def test_no_link_is_not_a_comparison_failure(self):                  # zero links: a `link` rule's business, unchanged
        inst = [{'id': 'P1', 'type': 'A4.InfrastructureComponent', 'name': 'One', 'attributes': {}}]
        f = evaluate({'A4': {'level': 'A4', 'instances': inst, 'relationships': []}}, [], MM, [DIFFER])[0]
        self.assertEqual(f['outcome'], 'compliant')


if __name__ == '__main__':
    unittest.main()
