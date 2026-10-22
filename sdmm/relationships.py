"""Render docs/relationships-planning.md from metamodel/level-relationships.json.

The JSON is the record of every within-level entity connection (constraint rows per level, plus catalogue
inheritance); the document is a projection of it, checked current by the test suite.
"""
from pathlib import Path
import argparse, json
from sdmm.metamodel import MM_DIR

LEVEL_RELS = MM_DIR / 'level-relationships.json'
DOC = MM_DIR.parent / 'docs' / 'relationships-planning.md'
LEVEL_NAMES = {'A1': 'A1 Business Architecture', 'A2': 'A2 Service Domain Architecture', 'A3': 'A3 Application Architecture', 'A4': 'A4 Technology Architecture'}
LEVEL_SOURCE = {'A1': 'ArchiMate 3.2 chapters 6 (Motivation), 7 (Strategy) and 8 (Business)', 'A2': "BIAN Service Landscape 14 metamodel, Control Record Model, Business Object Model and the Semantic API Practitioner Guide",
                'A3': 'ArchiMate 3.2 chapter 9 (Application) and TOGAF 10 (Solution Building Block); SDMM extension rows for API operations', 'A4': 'ArchiMate 3.2 chapter 10 (Technology); SDMM extension rows for Deployment and Deployment Environment'}


def load(path=LEVEL_RELS):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def render(lr=None):
    lr = lr or load()
    rows = lr['constraints']
    from collections import Counter
    out = ['# Relationships planning — within-level entity connections', '',
           'Generated from `metamodel/level-relationships.json` by `python -m sdmm.relationships`; the test suite checks this file is current. '
           'These are the connections **inside** each architecture (A1–A4), held by each level export\'s `relationships` list and enforced by `sdmm-graph check`. '
           'They are not mappings: the cross-level connections are planned in `docs/mapping-logic-planning.md` and recorded in `metamodel/new-mappings.json`.', '',
           '**Rule.** A within-level relationship is accepted when it matches a row for its level (through catalogue inheritance), or when its kind is `association` — ArchiMate\'s generic relationship, permitted between any two entities of one level and therefore not listed. Every row derives from the reference architecture the level\'s entities derive from (README › *Reference architecture provenance*).', '',
           '**Confidence and verification.** `high` = public BIAN source, or an SDMM definition; `medium` = paraphrased from the ArchiMate 3.2 / TOGAF 10 chapter structure, which is login-gated, so marked `unverified_archimate` / `unverified_togaf` until checked against the specification\'s relationship tables. `sdmm_definition` rows follow from how an SDMM extension entity is defined; `sdmm_reading` is SDMM\'s reading of a public BIAN page that states no explicit relationship.', '']
    tally = Counter((c['level'], c['confidence']) for c in rows)
    out += ['## Summary', '', '| Level | Reference source | Rows | high | medium |', '|---|---|---|---|---|']
    for l in ('A1', 'A2', 'A3', 'A4'):
        n = sum(1 for c in rows if c['level'] == l)
        out.append(f"| {LEVEL_NAMES[l]} | {LEVEL_SOURCE[l]} | {n} | {tally[(l, 'high')]} | {tally[(l, 'medium')]} |")
    out.append(f"| **Total** | | **{len(rows)}** | {sum(v for (l, c), v in tally.items() if c == 'high')} | {sum(v for (l, c), v in tally.items() if c == 'medium')} |")
    out.append('')
    for l in ('A1', 'A2', 'A3', 'A4'):
        out += [f'## {LEVEL_NAMES[l]}', '', f'Reference: {LEVEL_SOURCE[l]}.', '',
                '| ID | Official | Source entity | Kind | Target entity | Description | Reference source | Reasoning | Confidence | Verification |', '|---|---|---|---|---|---|---|---|---|---|']
        for c in rows:
            if c['level'] != l: continue
            out.append(f"| {c['id']} | {c.get('official_id') or '—'} | {c['source_type']} | {c['kind']} | {c['target_type']} | {c['description']} | {c['reference_source']} | {c['reasoning']} | {c['confidence']} | {c['verification']} |")
        out.append('')
    out += ['## Catalogue inheritance (is-a)', '', 'Not relationships in an export: the catalogue\'s `extends` links, through which a mapping\'s abstract or parent type resolves to a concrete instance.', '',
            '| ID | Entity | extends | Description | Reference source | Reasoning | Confidence | Verification |', '|---|---|---|---|---|---|---|---|']
    for x in lr['inheritance']:
        out.append(f"| {x['id']} | {x['entity']} | {x['extends']} | {x['description']} | {x['reference_source']} | {x['reasoning']} | {x['confidence']} | {x['verification']} |")
    out.append('')
    return '\n'.join(out) + '\n'


def main(argv=None):
    parser = argparse.ArgumentParser(prog='sdmm-relationships', description='Render docs/relationships-planning.md from metamodel/level-relationships.json.')
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args(argv)
    text = render()
    if args.check:
        ok = DOC.exists() and DOC.read_text(encoding='utf-8') == text
        print('up to date' if ok else 'STALE: regenerate with python -m sdmm.relationships'); return 0 if ok else 1
    DOC.write_text(text, encoding='utf-8'); print(f'wrote {DOC}'); return 0


if __name__ == '__main__':
    raise SystemExit(main())
