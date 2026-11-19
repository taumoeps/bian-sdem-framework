"""Write sdem-bian's data folder from SDEM's built-in BIAN (docs/design/sdem-bian-package-spec.md, BP-02, BP-11).

    python scripts/bian_package.py <sdem-extensions>/metamodel/bian/sdem_bian/data

The A2 metamodel, its within-layer rules, link types and inference rules, and the catalogue — verbatim, so the package and SDEM's
fallback start identical; the package's tests hold them identical while the fallback exists (BP-11)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sdem.parts import write_package_data  # noqa: E402

if __name__ == '__main__':
    if len(sys.argv) != 2: sys.exit(__doc__)
    print('\n'.join(write_package_data(sys.argv[1])))
