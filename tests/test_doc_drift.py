"""The current documents carry no out-of-date wording (scripts/doc_drift.py) — old command names, stale statuses,
hard-coded test counts, old release status, *imported* designs, real data in this public repository."""
import subprocess, sys, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class DocDriftTests(unittest.TestCase):
    def test_no_drift(self):
        r = subprocess.run([sys.executable, str(ROOT / 'scripts' / 'doc_drift.py')], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_the_check_catches_drift(self):
        sys.path.insert(0, str(ROOT / 'scripts'))
        import re, doc_drift
        hits = [why for line in ('run `sdem-graph check` first', 'Status: draft 2026', 'all 412 tests pass', 'load imported designs')
                for rx, why in doc_drift.RULES if re.search(rx, line)]
        self.assertEqual(len(hits), 4, hits)


    def test_the_onboarding_command_tables_match(self):  # the test script repeats the workflow's table; they must not drift apart
        import re
        def rows(f, start):
            s = (ROOT / f).read_text(encoding='utf-8'); t = s[s.index(start):]; t = t[:t.index('\n## ', 5)]
            return [l for l in t.splitlines() if re.match(r'^\| \d+ \|', l)]
        a = rows('docs/sdem-onboarding-workflow.md', '## 3. The commands in plain words')
        self.assertEqual(len(a), 14); self.assertEqual(a, rows('docs/use-case-example-4.md', '## The commands in plain words'))

if __name__ == '__main__':
    unittest.main()
