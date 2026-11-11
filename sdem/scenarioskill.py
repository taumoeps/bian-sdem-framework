"""Generate the agents' skill `sdem-scenarios` from docs/sdem-scenarios.md (AG-S01): the same jobs, in the same order, for an agent —
one source for people and agents. Written into .github/skills/ (what `sdem agents install` ships) and the repository's own
.claude/skills/ and .agents/skills/; `sdem model check` fails when any copy is stale.

  python -m sdem.scenarioskill            # write it
  python -m sdem.scenarioskill --check    # is it current?
"""
import argparse, re

from .paths import DATA_ROOT as ROOT

SRC = ROOT / 'docs' / 'sdem-scenarios.md'
OUTS = [ROOT / d / 'skills' / 'sdem-scenarios' / 'SKILL.md' for d in ('.github', '.claude', '.agents')]

HEAD = '''---
name: sdem-scenarios
description: Which SDEM commands to run, in what order, and who decides, for every job — {jobs}. Use when asked to do any of these jobs, when unsure which command comes next, or before using a command no other skill covers.
---

# SDEM jobs, end to end

> Generated from SDEM's [scenarios guide](../../../docs/sdem-scenarios.md) — the same steps a person reads. Do not edit: SDEM regenerates it.

**How to use it.** Find the job below. Where it names a **skill**, read that skill too — it has the detail. Before you run a command, get its exact options from SDEM, never from memory: `sdem commands <command> --json` (one command, e.g. `sdem commands "events assess" --json`) or `sdem <command> --help`. Add `--json` to every command and `--dry-run` before anything that writes. Every step marked **A person decides** is the architect's: prepare the exact command with their name, explain it, and ask — never run it with an agent's name (CTL-21). End with `sdem handback --workspace <dir> --json`.

'''


def render():
    text = SRC.read_text(encoding='utf-8')
    jobs = [re.sub(r'\s+', ' ', m.group(1)).strip() for m in re.finditer(r'^## \d+\. (.+)$', text, re.M)]
    body = text[text.index('**Conventions.**'):]
    body = body.replace('[CLI reference](reference/cli-reference.md)', '`sdem commands <command> --json`')
    body = re.sub(r'\]\((?!#)(?!https?:)([^)]+)\)', r'](../../../docs/\1)', body)   # from the skill's folder; sdem agents install pins them to this version
    jobs_txt = '; '.join(j[0].lower() + j[1:] for j in jobs)
    return HEAD.format(jobs=jobs_txt) + body.rstrip() + '\n'


def main(argv=None):
    ap = argparse.ArgumentParser(prog='sdem-scenarioskill'); ap.add_argument('--check', action='store_true'); a = ap.parse_args(argv)
    t = render()
    if a.check:
        stale = [o for o in OUTS if not o.exists() or o.read_text(encoding='utf-8') != t]
        print('sdem-scenarios skill: ' + ('up to date' if not stale else 'STALE: regenerate with sdem model regenerate — ' + ', '.join(str(o.relative_to(ROOT)) for o in stale)))
        return 1 if stale else 0
    for o in OUTS:
        o.parent.mkdir(parents=True, exist_ok=True); o.write_text(t, encoding='utf-8')
    print('wrote ' + ', '.join(str(o.relative_to(ROOT)) for o in OUTS)); return 0


if __name__ == '__main__':
    raise SystemExit(main())
