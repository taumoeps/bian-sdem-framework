"""Flag out-of-date wording in the current documents — the drift the 2026-10-29 audit kept finding by hand.

Scans every current Markdown document (not docs/history/, the reasoning records, the CHANGELOG or test fixtures) and
the Copilot files for wording SDEM no longer uses. Run by tests/test_doc_drift.py on every push.

    python scripts/doc_drift.py          # lists findings; exit 1 if any
"""
import re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# records kept as written (docs/README.md: Reasoning and evidence; History) — they keep their words
RECORDS = {'docs/design/mapping-logic-planning.md', 'docs/design/mapping-execution.md', 'docs/evidence/use-case-testing.md', 'docs/design/inference-audit.md',
           'docs/design/architecture-metamodel-high-level-spec.md', 'docs/evidence/relationships-testing.md', 'CHANGELOG.md', 'docs/design/PUBLICATION_CHECKLIST.md'}
RECORD_DIRS = ('docs/history/', 'docs/design/drafts/', 'docs/design/baseline/', 'tests/fixtures/')

RULES = [
    (r'(?<![\w./-])(sdem-graph|sdem-infer|sdem-aid|sdem-accept|sdem-validate|sdem-diff|sdmm-[a-z]+)\b(?![./-])', 'old command name — use `sdem <verb>`'),
    (r'\bpython -m sdmm\b|`sdmm/`', 'the sdmm package was removed'),
    (r'(?i)\bstatus:\s*\**\s*draft\b', 'a "draft" status — approved or built since?'),
    (r'\b\d{3} tests\b', 'a hard-coded test count drifts — say "the full suite" or "about N"'),
    (r'(?i)v0\.7\.0 released|not yet released|nothing (has been )?released since', 'release status out of date'),
    (r'(?i)\bimport(ed|ing)? (past|existing|historical) designs\b|\bimported designs\b', 'say "onboard(ed) designs"'),
    (r'(?i)organisation\'s (own )?copy of (the|this) (project|repository)', 'real data goes in a private estate repository'),
    (r'git add estates/history', 'estates/ is ignored here — real estates go in a private estate repository'),
    (r'(?i)python 3\.9\b(?! (is|was|reached|reaches))', 'SDEM needs Python 3.10 or later'),
    (r'(?i)render[^.\n]{0,40}www\.plantuml\.com|plantuml\.render"\s*:\s*"PlantUMLServer', 'PlantUML renders locally'),
]


def current_docs():
    files = subprocess.run(['git', 'ls-files', '-z', '--', '*.md'], cwd=ROOT, capture_output=True, text=True).stdout.split('\0')
    return sorted({f for f in files if f and f not in RECORDS and not f.startswith(RECORD_DIRS) and (ROOT / f).exists()})


def findings():
    out = []
    for f in current_docs():
        for n, line in enumerate((ROOT / f).read_text(encoding='utf-8').splitlines(), 1):
            if 'drift-ok' in line: continue        # a deliberate mention, e.g. explaining an old name
            for rx, why in RULES:
                m = re.search(rx, line)
                if m: out.append((f, n, m.group(0), why))
    return out


if __name__ == '__main__':
    fs = findings()
    for f, n, hit, why in fs: print(f'{f}:{n}: "{hit}" — {why}')
    print(f'{len(fs)} finding(s)'); sys.exit(1 if fs else 0)
