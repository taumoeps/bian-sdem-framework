"""Link an installed extension's examples into examples/ (0.22, R-D6) — for CI and local runs that read examples/<name> directly.

The banking designs moved to sdem-bian; SDEM's tests find them through tests/needs.py, and this script gives the workflow steps
and scripts that name `examples/payment-initiation` the same folder. It links (copies where linking is not allowed), never
overwrites, and `--remove` takes away only what it linked.

    python scripts/link_extension_examples.py            # link
    python scripts/link_extension_examples.py --remove   # unlink
"""
import os, shutil, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def pairs():
    from sdem import parts
    for r in parts.example_roots()[1:]:
        for c in sorted(r.iterdir()):
            if c.name == '0.20' and c.is_dir():
                for cc in sorted(c.iterdir()): yield cc, ROOT / 'examples' / '0.20' / cc.name
            else: yield c, ROOT / 'examples' / c.name


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    n = 0
    for src, dst in pairs():
        if '--remove' in argv:
            if dst.is_symlink(): dst.unlink(); n += 1
            continue
        if dst.exists() or dst.is_symlink(): continue
        try: os.symlink(src, dst, target_is_directory=src.is_dir())
        except OSError: (shutil.copytree if src.is_dir() else shutil.copy2)(src, dst)
        n += 1
    print(f"{'unlinked' if '--remove' in argv else 'linked'} {n} example(s)")
    if not n and '--remove' not in argv and not list(pairs()):
        print('no extension examples found — install sdem-bian', file=sys.stderr); return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
