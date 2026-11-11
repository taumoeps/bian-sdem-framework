"""The CLI reference and the scenarios guide (CR-01…CR-03): the reference is generated and current; every `sdem …` command in the
scenarios guide, the README and the user guide's code blocks names a command that exists and only options it has — so the guides
cannot drift from the CLI silently."""
import contextlib, io, re, shlex, sys, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from sdem import agent, clidoc   # noqa: E402
from sdem.cli import JOURNEYS, ESTATE_COMMANDS, _run   # noqa: E402

COMMON = {'--json', '--dry-run', '--limit', '-h', '--help'}


def catalogue():
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        return agent.catalogue({k: v for k, v in JOURNEYS.items() if k != 'commands'}, _run)['commands']


def commands_in(path):
    """(line number, command line) for every `sdem …` in a fenced code block — continuations joined, comments dropped."""
    out, fence, buf, start = [], False, '', 0
    for n, line in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
        if line.strip().startswith('```'): fence = not fence; buf = ''; continue
        if not fence: continue
        s = re.sub(r'\s+#\s.*$', '', line).rstrip()
        if not buf: start = n
        if s.endswith('\\'): buf += s[:-1] + ' '; continue
        full = (buf + s).strip(); buf = ''
        for part in re.split(r'\s*(?:&&|;|\|)\s*', full):
            if part.startswith('sdem '): out.append((start, part))
    return out


class Checks:
    def __init__(self):
        self.cmds = catalogue()

    def problems(self, line):
        try: toks = shlex.split(line)
        except ValueError as e: return [f'cannot read: {e}']
        words = toks[1:]
        if words and words[0] in ('--version', '-V', '--help', '-h'): return []   # sdem's own top-level flags
        name = None
        for k in range(len(words), 0, -1):
            cand = ' '.join(words[:k])
            if cand in self.cmds and not any(w.startswith('-') for w in words[:k]): name = cand; break
        if not name: return [f"no such command: sdem {' '.join(w for w in words[:2] if not w.startswith('-'))}"]
        c = self.cmds[name]
        if 'group' in c and not (c.get('options') or c.get('positionals')):
            return [f'sdem {name} needs a subcommand: ' + ', '.join(c['group'])]
        valid = set(COMMON) | {x for o in c.get('options', []) for x in [o['name']] + o.get('aliases', [])}
        if name.split()[0] in ESTATE_COMMANDS: valid |= {'--workspace', '--estate'}
        if name.split()[0] in ('model',): return []   # the owner's maintenance commands parse their own options
        bad = [t.split('=')[0] for t in words if t.startswith('-') and not re.fullmatch(r'-?\d+(\.\d+)?', t) and t.split('=')[0] not in valid]
        return [f'sdem {name} has no option {b}' for b in bad]


class ReferenceTests(unittest.TestCase):
    def test_the_reference_is_current_and_complete(self):   # CR-01
        out = clidoc.OUT.read_text(encoding='utf-8')
        self.assertEqual(out, clidoc.render(), 'docs/reference/cli-reference.md is stale — run sdem model regenerate')
        for name in catalogue(): self.assertIn(f'### sdem {name}\n', out)
        self.assertIn('### sdem document verify\n', out); self.assertIn('`--organisation`', out)


class GuideTests(unittest.TestCase):   # CR-02, CR-03
    @classmethod
    def setUpClass(cls): cls.chk = Checks()

    def check(self, path, at_least):
        found = commands_in(path)
        self.assertGreaterEqual(len(found), at_least, path)
        bad = [f'{path.name}:{n}: {p}' for n, line in found for p in self.chk.problems(line)]
        self.assertFalse(bad, '\n' + '\n'.join(bad))

    def test_scenarios(self): self.check(ROOT / 'docs' / 'sdem-scenarios.md', 80)
    def test_readme(self): self.check(ROOT / 'README.md', 15)
    def test_user_guide(self): self.check(ROOT / 'docs' / 'sdem-workbench-user-guide.md', 30)

    def test_every_scenario_names_who_decides_and_links_the_reference(self):
        text = (ROOT / 'docs' / 'sdem-scenarios.md').read_text(encoding='utf-8')
        self.assertIn('reference/cli-reference.md', text)
        self.assertEqual(len(re.findall(r'^## \d+\. ', text, re.M)), 15)

    def test_a_wrong_option_is_caught(self):
        self.assertTrue(self.chk.problems('sdem new --workspace w --persn x'))
        self.assertTrue(self.chk.problems('sdem frobnicate --workspace w'))
        self.assertFalse(self.chk.problems('sdem build --workspace w --out w/graph'))


if __name__ == '__main__':
    unittest.main()
