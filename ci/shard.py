"""Run one shard of SDEM's test suite (MIP-07: cheap change — CI runs the suite in parallel parts, not one long step).

    python ci/shard.py <parts> <part> [log]      e.g.  python ci/shard.py 4 1

The test files are split into <parts> groups of about equal size (largest first, each to the lightest group), the same split every
time; part is 1…parts. Every test file is in exactly one part, so the parts together are the whole suite. Exit code 0 when the part passes.
"""
import sys, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def parts(n):
    files = sorted((ROOT / 'tests').glob('test_*.py'), key=lambda p: (-p.stat().st_size, p.name))
    groups, load = [[] for _ in range(n)], [0] * n
    for f in files:
        i = load.index(min(load)); groups[i].append(f.stem); load[i] += f.stat().st_size
    return groups


if __name__ == '__main__':
    n, k = int(sys.argv[1]), int(sys.argv[2])
    mods = sorted(parts(n)[k - 1])
    sys.path.insert(0, str(ROOT / 'tests')); sys.path.insert(0, str(ROOT))
    suite = unittest.defaultTestLoader.loadTestsFromNames(mods)
    print(f'part {k} of {n}: {len(mods)} test files, {suite.countTestCases()} tests', flush=True)
    stream = open(sys.argv[3], 'w', encoding='utf-8') if len(sys.argv) > 3 else sys.stderr
    ok = unittest.TextTestRunner(stream=stream, verbosity=1).run(suite).wasSuccessful()
    sys.exit(0 if ok else 1)
