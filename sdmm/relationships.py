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
           '**Inference (A1, A3, A4).** ArchiMate 3.2 and TOGAF 10 are login-gated, so every row outside A2 carries an explicit inference: the ArchiMate concept of each end (SDMM extensions through the concept they extend), the generic-metamodel pattern the row instantiates, the reasoning, SDMM\'s inference confidence, and the independent test — a lookup in the open-source Archi tool\'s relationship matrix (`relationships.xml`, github.com/archimatetool/archi), which implements the specification\'s permitted relationships per concept pair with the letters c composition, g aggregation, i assignment, r realization, v serving, a access, f flow, t triggering, s specialization, o association. The test plan for running those lookups is `docs/relationships-testing.md` §6.', '',
           '**Confidence and verification.** `high` = public BIAN source, or an SDMM definition; `medium` = paraphrased from the ArchiMate 3.2 / TOGAF 10 chapter structure, which is login-gated, so marked `unverified_archimate` / `unverified_togaf` until checked against the specification\'s relationship tables; `verified_against_archi` = confirmed by the open-source Archi relationship matrix (an implementation of those tables, cited by commit in the record), which is as far as verification can go without Open Group access. `sdmm_definition` rows follow from how an SDMM extension entity is defined; `sdmm_reading` is SDMM\'s reading of a public BIAN page that states no explicit relationship.', '']
    tally = Counter((c['level'], c['confidence']) for c in rows)
    out += ['## Summary', '', '| Level | Reference source | Rows | high | medium |', '|---|---|---|---|---|']
    for l in ('A1', 'A2', 'A3', 'A4'):
        n = sum(1 for c in rows if c['level'] == l)
        out.append(f"| {LEVEL_NAMES[l]} | {LEVEL_SOURCE[l]} | {n} | {tally[(l, 'high')]} | {tally[(l, 'medium')]} |")
    out.append(f"| **Total** | | **{len(rows)}** | {sum(v for (l, c), v in tally.items() if c == 'high')} | {sum(v for (l, c), v in tally.items() if c == 'medium')} |")
    out.append('')
    for l in ('A1', 'A2', 'A3', 'A4'):
        out += [f'## {LEVEL_NAMES[l]}', '', f'Reference: {LEVEL_SOURCE[l]}.', '',
                ('| ID | Official | Source entity | Kind | Target entity | Description | Reference source | Reasoning | Confidence | Verification |' if l == 'A2' else
                 '| ID | Source entity | Kind | Target entity | Description | ArchiMate concepts | Inferred pattern | Inference reasoning | Inference conf. | Independent test | Verification |'),
                ('|---|---|---|---|---|---|---|---|---|---|' if l == 'A2' else '|---|---|---|---|---|---|---|---|---|---|---|')]
        for c in rows:
            if c['level'] != l: continue
            if l == 'A2':
                out.append(f"| {c['id']} | {c.get('official_id') or '—'} | {c['source_type']} | {c['kind']} | {c['target_type']} | {c['description']} | {c['reference_source']} | {c['reasoning']} | {c['confidence']} | {c['verification']} |")
            else:
                i = c['inference']
                out.append(f"| {c['id']} | {c['source_type']} | {c['kind']} | {c['target_type']} | {c['description']} | {i['archimate_source']} → {i['archimate_target']} | {i['pattern']} | {i['reasoning']} | {i['confidence']} | {i['test']} | {c['verification']} |")
        out.append('')
    out += ['## Catalogue inheritance (is-a)', '', 'Not relationships in an export: the catalogue\'s `extends` links, through which a mapping\'s abstract or parent type resolves to a concrete instance.', '',
            '| ID | Entity | extends | Description | Reference source | Reasoning | Confidence | Verification |', '|---|---|---|---|---|---|---|---|']
    for x in lr['inheritance']:
        out.append(f"| {x['id']} | {x['entity']} | {x['extends']} | {x['description']} | {x['reference_source']} | {x['reasoning']} | {x['confidence']} | {x['verification']} |")
    out.append('')
    # ---- verification status, from the record and the test log
    from collections import Counter as _C
    vc = _C(c['verification'] for c in rows)
    MEANING = {'verified': 'checked against BIAN\'s public pages (A2)', 'verified_against_archi': 'concept pair and kind listed by the open-source Archi relationship matrix — an implementation of the ArchiMate 3.2 relationship tables, cited by commit below',
               'sdmm_reading': 'SDMM\'s reading of a public BIAN page that states no explicit relationship', 'sdmm_definition': 'follows from an SDMM extension entity\'s definition', 'unverified_archimate': 'paraphrased from ArchiMate chapter structure; not yet checked', 'unverified_togaf': 'paraphrased from TOGAF; no public oracle'}
    out += ['## Verification status', '', 'How far each row has been checked, and against what. `verified_against_archi` is as far as ArchiMate-derived rows can go without Open Group access; the two TOGAF rows have no public oracle.', '',
            '| Status | Rows | Meaning |', '|---|---|---|']
    for k, n in sorted(vc.items(), key=lambda x: -x[1]):
        out.append(f"| {k} | {n} | {MEANING.get(k, '')} |")
    o = lr.get('verification_oracle')
    if o:
        out += ['', f"**Oracle.** {o['name']}: `{o['repo']}` › `{o['path']}`, read at commit `{o['commit_read']}` (file last changed `{o['file_last_changed']}`, declares version {o['declared_version']}), {o['date']}. Nothing from the oracle is stored in this repository; each test-log entry records only the letters listed for the row's concept pair. {o.get('note', '')}"]
    ic = _C(c['inference']['confidence'] for c in rows if c.get('inference'))
    oc = _C(c['inference'].get('oracle_verdict', 'not tested') for c in rows if c.get('inference'))
    out += ['', '**Inference calibration.** Inference confidence before the oracle test versus the oracle verdict:', '', '| Inference confidence | Rows | Oracle verdict |', '|---|---|---|']
    for conf in ('high', 'medium', 'low'):
        sub = [c for c in rows if c.get('inference') and c['inference']['confidence'] == conf]
        verdicts = _C(c['inference'].get('oracle_verdict', 'not tested') for c in sub)
        out.append(f"| {conf} | {len(sub)} | " + ', '.join(f"{v}: {n}" for v, n in sorted(verdicts.items(), key=lambda x: -x[1])) + ' |')
    log = MM_DIR / 'relationships-test-log.json'
    out += ['', '## Test history', '', 'The test plan is `docs/relationships-testing.md`; its results sections and `metamodel/relationships-test-log.json` hold the per-row evidence.', '',
            '| Phase | What was tested | Result |', '|---|---|---|',
            '| 1 (2026-10-23) | provenance, grounding, consistency, enforcement probes, coverage, rule dependencies — all 131 rows and 12 inheritance links | 0 fail; 3 artefact rows not enforceable; 6 findings applied in v0.5.17 |',
            f"| 2 (2026-10-23) | every A1 / A3 / A4 inference against the Archi relationship matrix | {oc.get('confirmed', 0)} confirmed, {oc.get('confirmed, alternative accepted', 0)} confirmed via stated alternative, 0 contradicted, {sum(1 for c in rows if c.get('inference') and 'TOGAF' in c['inference']['pattern'])} not testable (TOGAF); applied in v0.5.20 |" + ('' if log.exists() else ' (log file absent)'),
            '']
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
