"""Generate examples/reference-structure/ from metamodel/level-relationships.json: two instances per concrete entity,
one relationship per enforceable constraint row (relationship name = row ID). Every row the record allows is
thereby exercised on committed data and accepted by sdmm-graph check."""
from pathlib import Path
import argparse, json
from sdmm.metamodel import Metamodel, MM_DIR

OUT = MM_DIR.parent / 'examples' / 'reference-structure'
FILES = {"A1": "a1-business.json", "A2": "a2-service-domain.json", "A3": "a3-application.json", "A4": "a4-technology.json"}


def render(metamodel=None, level_rels=None):
    mm = metamodel or Metamodel.load()
    lr = level_rels or json.loads((MM_DIR / 'level-relationships.json').read_text(encoding='utf-8'))
    short = lambda t: t.split('.')[1]
    docs = {}
    for lvl in FILES:
        ents = [t for t, e in mm.entities.items() if e['level'] == lvl and not e.get('abstract') and not e.get('artefact')]
        inst = [{"id": f"RS-{short(t)}-{n}", "type": t, "version": "1.0", "name": f"{short(t)} {n} (structure conformance)", "lifecycle_status": "active",
                 "description": f"Synthetic instance of {t} carrying one relationship per constraint row of {lvl}; no business meaning."} for t in ents for n in (1, 2)]
        rels = [{"source": f"RS-{short(c['source_type'])}-1", "kind": c['kind'], "target": f"RS-{short(c['target_type'])}-{2 if c['source_type'] == c['target_type'] else 1}", "name": c['id']}
                for c in lr['constraints'] if c['level'] == lvl and c.get('enforceable') is not False]
        docs[lvl] = {"level": lvl, "model_id": f"reference-structure-{lvl.lower()}", "model_version": "2026.10", "metamodel_version": "0.4.0", "source_system": "SDMM-GENERATED-FROM-RECORD", "instances": inst, "relationships": rels}
    return docs


def main(argv=None):
    parser = argparse.ArgumentParser(prog='sdmm-structure', description='Generate examples/reference-structure/ from level-relationships.json.')
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args(argv)
    docs = render(); rc = 0
    for lvl, name in FILES.items():
        text = json.dumps(docs[lvl], indent=2, ensure_ascii=False) + '\n'; path = OUT / name
        if args.check:
            ok = path.exists() and path.read_text(encoding='utf-8') == text; rc |= 0 if ok else 1
            print(f"{name}: {'up to date' if ok else 'STALE: regenerate with python -m sdmm.structure'}")
        else:
            path.write_text(text, encoding='utf-8'); print(f'wrote {path}')
    return rc


if __name__ == '__main__':
    raise SystemExit(main())
