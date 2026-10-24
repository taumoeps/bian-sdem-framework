"""The high-level metamodel specification is frozen (owner's instruction, 2026-10-25); the detail-level spec is current."""
import hashlib, json, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HIGH = ROOT / 'docs' / 'architecture-metamodel-high-level-spec.md'
# Pinned content of the owner's high-level spec. Change only with the owner's explicit approval of a specific edit.
HIGH_SHA256 = '2e6a7d70d1d5006d18b506c9aaf05439f9042021bd9d3989fb327e49072f4bf1'


class HighLevelSpecTests(unittest.TestCase):
    def test_high_level_spec_is_unchanged(self):
        self.assertEqual(hashlib.sha256(HIGH.read_bytes()).hexdigest(), HIGH_SHA256,
                         'docs/architecture-metamodel-high-level-spec.md changed: the owner must approve any edit (then update HIGH_SHA256)')


class DetailSpecTests(unittest.TestCase):
    def test_current(self):
        from sdem.metamodel_spec import main
        import contextlib, io
        with contextlib.redirect_stdout(io.StringIO()): self.assertEqual(main(['--check']), 0)

    def test_every_gap_is_referenced_and_complete(self):
        text = (ROOT / 'docs' / 'architecture-metamodel-detail-level-spec.md').read_text(encoding='utf-8')
        for g in json.loads((ROOT / 'metamodel' / 'metamodel-spec-gaps.json').read_text(encoding='utf-8'))['gaps']:
            for k in ('kind', 'high_level_section', 'high_level_says', 'implemented', 'recommendation', 'status'): self.assertTrue(g[k], f"{g['id']} {k}")
            self.assertIn(f"**Gap {g['id']}**", text, g['id'])

    def test_catalogue_alignment_is_computed_from_the_high_level_tables(self):
        from sdem.metamodel_spec import high_level_catalogue
        rows = high_level_catalogue(HIGH.read_text(encoding='utf-8'))
        self.assertEqual(len(rows), 41)
        self.assertEqual(rows['A4.Deployment'], ('sdem_extension', 'composite'))


if __name__ == '__main__':
    unittest.main()
