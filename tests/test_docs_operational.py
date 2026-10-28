"""The documentation is operational: every current document says what it is at the top, every link resolves (files and
headings), and document changes need the owner's review (CODEOWNERS)."""
import re, subprocess, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FROZEN = 'docs/design/architecture-metamodel-high-level-spec.md'
LABEL = re.compile(r'\*\*Status|Generated (by|from)|A record, in its original words', re.I)


def tracked_markdown():
    out = subprocess.run(['git', 'ls-files', '-z', '--', '*.md'], cwd=ROOT, capture_output=True, text=True).stdout.split('\0')
    return [f for f in out if f and not f.startswith('tests/fixtures/') and (ROOT / f).exists()]


def slug(heading):  # GitHub's heading anchors
    h = re.sub(r'[`*_]|<[^>]+>', '', heading.strip().lower())
    return re.sub(r'[^\w\- ]', '', h, flags=re.UNICODE).replace(' ', '-')


def anchors(path, cache={}):
    if path not in cache:
        text = re.sub(r'```.*?```', '', path.read_text(encoding='utf-8'), flags=re.S)
        seen, out = {}, set()
        for h in re.findall(r'^#{1,6}\s+(.+?)\s*#*$', text, re.M):
            s = slug(h); n = seen.get(s, 0); seen[s] = n + 1
            out.add(s if n == 0 else f'{s}-{n}')
        cache[path] = out
    return cache[path]


class DocsOperationalTests(unittest.TestCase):
    def test_every_current_document_says_what_it_is(self):
        docs = sorted((ROOT / 'docs').glob('*.md')) + [ROOT / 'docs' / d / 'README.md' for d in ('design', 'reference', 'evidence', 'history')]
        missing = [str(f.relative_to(ROOT)) for f in docs
                   if not LABEL.search('\n'.join(f.read_text(encoding='utf-8').split('\n')[:8]))]
        self.assertEqual(missing, [], 'add "> **Status: …**" under the title (current, approved, proposed, built, or a record)')

    def test_every_link_resolves(self):
        broken = []
        for f in tracked_markdown():
            if f == FROZEN: continue   # the owner's pinned spec cannot be edited; its links point where documents were when it was frozen
            src = ROOT / f
            text = re.sub(r'```.*?```', '', src.read_text(encoding='utf-8'), flags=re.S)
            for target in re.findall(r'\]\(([^)\s]+)\)', text):
                if re.match(r'^(https?|mailto):', target): continue
                path, _, frag = target.partition('#')
                dest = (src.parent / path).resolve() if path else src
                if not dest.exists(): broken.append(f'{f}: {target} (no such file)'); continue
                if frag and dest.suffix == '.md' and frag not in anchors(dest): broken.append(f'{f}: {target} (no such heading)')
        self.assertEqual(broken, [])

    def test_the_top_level_is_for_people_who_use_sdem(self):  # builders' documents live in design/, evidence/, reference/, history/
        top = sorted(f.name for f in (ROOT / 'docs').glob('*.md'))
        self.assertEqual(top, sorted(['README.md', 'glossary.md', 'sdem-overview.md', 'sdem-workbench-user-guide.md', 'sdem-onboarding-workflow.md',
                                      'sdem-rulebook-guide.md', 'sdem-architecture.md', 'sdem-configuration.md', 'sdem-administration.md',
                                      'sdem-operating-model.md', 'sdem-adoption-checklist.md', 'sdem-repository-protection.md', 'sdem-copilot-setup.md', 'sdem-agent-platform-spike.md', 'sdem-pilot-plan.md', 'sdem-planning-with-aid.md']))
        for d in ('design', 'reference', 'evidence', 'history'):
            self.assertTrue((ROOT / 'docs' / d / 'README.md').exists(), d)

    def test_document_changes_need_the_owners_review(self):
        owners = (ROOT / '.github' / 'CODEOWNERS').read_text(encoding='utf-8')
        for path in ('/docs/', '/docs/design/architecture-metamodel-high-level-spec.md', '/README.md'):
            self.assertRegex(owners, r'(?m)^' + re.escape(path) + r'\s+@\S+', path)


if __name__ == '__main__':
    unittest.main()
