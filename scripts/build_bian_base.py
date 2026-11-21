"""Rebuild the base BIAN (bian/base-<release>.json) and its object index (bian/objects-<release>.json, BO-01) from a downloaded BIAN Semantic API release (BB-M01).

Download the release folder from github.com/bian-official/public (e.g. release14.0.0/semantic-apis/oas3/yamls), then:

    python scripts/build_bian_base.py ~/bian/release14.0.0

Also run scripts/bian_import_check.py on the same folder, update bian/README.md and the CHANGELOG with the release, and
remove the previous base file.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from sdem.bian import dump_index, dump_pack, object_index, pack, read_release  # noqa: E402
from sdem.files import write_text  # noqa: E402

domains, refused = read_release(sys.argv[1])
if refused:
    print('not built — files not read:\n  ' + '\n  '.join(refused)); sys.exit(1)
p = pack(domains)
out = ROOT / 'bian' / f"base-{p['release']}.json"
write_text(out, dump_pack(p))
print(f"wrote {out.relative_to(ROOT)}: {len(domains)} service domains of BIAN release {p['release']}")
ix = object_index(domains)   # BO-01: the business objects, typed fields only, beside the base
oi = ROOT / 'bian' / f"objects-{ix['release']}.json"
write_text(oi, dump_index(ix))
print(f"wrote {oi.relative_to(ROOT)}: {sum(len(v) for v in ix['domains'].values())} business objects of {len(ix['domains'])} service domains, {len(ix['definitions'])} distinct definitions")
