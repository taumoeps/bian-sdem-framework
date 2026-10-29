"""Maintainer check (docs/design/sdem-bian-import-spec.md, "Open before building"): `sdem bian` against a real BIAN release.

Reads every file of a downloaded release folder, then imports every service domain and checks the result with the
metamodel. Domains whose pattern cannot be derived get a placeholder (TEST ONLY — never for real use) so the whole
release is exercised. Nothing is written. Not run in CI: BIAN's files are not kept in this repository.

    python scripts/bian_import_check.py ~/bian/release14.0.0
"""
import sys, time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from sdem.bian import build, check, derive, read_release  # noqa: E402
from sdem.metamodel import Metamodel  # noqa: E402

t = time.time()
domains, refused = read_release(sys.argv[1])
placeholder = {d['name']: ('TEST ONLY ' + d['name'], 'PROCESS') for d in domains if not derive(d['control_record'])[0]}
dataset, rep = build(domains, Metamodel.load().version, patterns=placeholder)
errors, warnings = check(dataset)
print(f"files read {len(domains)}, refused {len(refused)}; derived {len(rep['derived'])}, placeholder {len(placeholder)} (test only)")
print(f"records {len(dataset['instances'])}, links {len(dataset['relationships'])}: " + ', '.join(f'{k.split(".")[1]} {v}' for k, v in sorted(Counter(i['type'] for i in dataset['instances']).items())))
print(f"metamodel: {len(errors)} error(s), {len(warnings)} advice; {time.time() - t:.1f}s")
for r in refused: print('  refused:', r)
for e in errors[:15]: print('  error:', e)
sys.exit(1 if errors or refused else 0)
