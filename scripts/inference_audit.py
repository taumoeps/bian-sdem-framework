"""One-off inference audit of SDEM's records (2026-10-23). Reads the records; the only judgement is ATTR_SOURCE."""
import json, glob
from collections import Counter, defaultdict
from pathlib import Path
R = Path(__file__).resolve().parents[1]
E = [e for f in sorted(glob.glob(str(R / 'metamodel/a[1-4]-*.json'))) for e in json.load(open(f))['entities']]
conv = json.load(open(R / 'metamodel/export-conventions.json'))['conventions']
lr = json.load(open(R / 'metamodel/level-relationships.json'))
rules = json.load(open(R / 'metamodel/relationship-rules.json'))['mappings']
off = {m['id']: m for m in json.load(open(R / 'metamodel/official-mappings.json'))['mappings']}

# ---- judgement: source of each documented attribute
B, O, AR, T, S, I = 'BIAN (public)', 'OpenAPI (public)', 'ArchiMate relationship or concept held as attribute', 'TOGAF (login-gated)', 'SDEM-defined', 'institution data'
P = 'other public standard (Dublin Core, W3C, ISO 20022, SPDX, public legislation …)'
_REC = json.load(open(R / 'metamodel/entity-attributes.json'))
_MAP = {'BIAN': B, 'OpenAPI': O, 'ArchiMate relationship': AR, 'ArchiMate concept': AR, 'TOGAF': T, 'SDEM': S, 'institution': I, 'Dublin Core': P, 'W3C ORG': P, 'W3C SKOS': P, 'public legislation': P, 'BIAN concept': B, **{k: P for k in ('W3C', 'ISO 20022', 'AsyncAPI', 'SPDX', 'CycloneDX', 'SemVer', 'NIST', 'IANA', 'ISO 3166', 'Kubernetes', 'OCI')}}
ATTR_SOURCE = {f"{x['entity']}.{x['name']}": _MAP[x['source']] for x in _REC['attributes'] if x['status'] == 'active'}
ATTR_SOURCE.update({f"common.{x['name']}": _MAP[x['source']] for x in _REC.get('common_attributes', [])})
attrs = {f'{e}.{k}' for e, ks in conv.items() for k in ks} - {'A1.BusinessCapability.description'}
assert attrs <= set(ATTR_SOURCE), (attrs - set(ATTR_SOURCE))
GROUNDED_ATTR = {B, O}; INFER_ATTR = {AR, S}; GATED = {T}

def def_class(e):
    ds, st = e['definition_source'], e['evidence_status']
    if ds in ('bian_reference', 'archimate_native') and st in ('confirmed_in_official_source', 'pending_release_validation'): return 'grounded'
    if ds in ('bian_aligned', 'archimate_aligned', 'togaf_informed'): return 'aligned (interpreted)'
    return 'SDEM extension (inferred)'

WL = {'verified': 'grounded', 'verified_against_archi': 'inferred, oracle-confirmed', 'sdem_definition': 'SDEM definition', 'sdem_reading': 'inferred', 'unverified_togaf': 'inferred, unverified', 'unverified_archimate': 'inferred, unverified'}
def xl_class(m):
    v = off[m['id']]['verification']
    if v in ('verified', 'verified_intent_or_target_only'): return 'official'
    if v in ('unverified_archimate', 'unverified_w135', 'unpublished'): return 'cited, unverified'
    if v == 'sdem_definition': return 'SDEM definition'
    return 'inferred (no official source)'
XL_EXCLUDE = {'bian_internal', 'not_a_mapping', 'historical_method', 'subsumed', 'not_encodable'}

rows = []; tot = defaultdict(Counter)
for e in E:
    t = e['type']; dc = def_class(e); tot['definition'][dc] += 1
    ea = {k.split('.', 2)[2]: v for k, v in ATTR_SOURCE.items() if k.startswith(t + '.')}
    for v in ea.values(): tot['attribute'][v] += 1
    wl = Counter(WL.get(c['verification'], c['verification']) for c in lr['constraints'] if t in (c['source_type'], c['target_type']))
    xl = [m for m in rules if t in (m['source'], m['target']) and m['rule_decision'] not in XL_EXCLUDE]
    xc = Counter(xl_class(m) for m in xl)
    rows.append((t, e['level'], (e.get('reference') or {}).get('standard', '—'), (e.get('reference') or {}).get('concept') or '—', dc, e['evidence_status'], ea, wl, xc, [m['id'] for m in xl]))
for c in lr['constraints']: tot['within'][WL.get(c['verification'], c['verification'])] += 1
for m in rules:
    if m['rule_decision'] not in XL_EXCLUDE: tot['cross'][xl_class(m)] += 1

def pct(c, keys): n = sum(c.values()); k = sum(c[x] for x in keys); return f"{k} of {n} ({round(100 * k / n)}%)"
out = ['# SDEM inference audit', '',
       'A snapshot taken 2026-10-23 by `python scripts/inference_audit.py` from the records (`metamodel/`, `schema/`). It answers one question: **without access to the login-gated standards or a standards MCP server, how much of SDEM is inferred rather than taken from a verifiable public source?** Counts are computed by script from the records; attribute sources are read from `metamodel/entity-attributes.json` (see `architecture-attribute-design.md`).', '',
       '**Definitions used.** *Grounded*: stated in a public source anyone can check (BIAN public portal and Semantic API guide; ArchiMate concept names; OpenAPI). *Oracle-confirmed*: inferred by SDEM, then confirmed against the open-source Archi implementation of the ArchiMate relationship tables. *Inferred*: SDEM\'s own reading or design, with reasoning recorded, tested by the use cases but not by a standard. *Gated*: cited to TOGAF or the ArchiMate text and not checkable without an Open Group login.', '',
       '## 1. Summary by layer', '',
       '| Layer | Total | Grounded | Oracle-confirmed | Inferred | Gated / unverified |', '|---|---|---|---|---|---|',
       f"| Entity definitions | {sum(tot['definition'].values())} | {tot['definition']['grounded']} | — | {tot['definition']['SDEM extension (inferred)'] + tot['definition']['aligned (interpreted)']} ({tot['definition']['SDEM extension (inferred)']} SDEM extensions, {tot['definition']['aligned (interpreted)']} interpreted alignments) | 0 |",
       f"| Attributes | {sum(tot['attribute'].values())} | {tot['attribute'][B] + tot['attribute'][O] + tot['attribute'][P]} (BIAN {tot['attribute'][B]}, OpenAPI {tot['attribute'][O]}, other public standards {tot['attribute'][P]}) | — | {tot['attribute'][AR] + tot['attribute'][S]} (relationship held as attribute {tot['attribute'][AR]}, SDEM-defined {tot['attribute'][S]}) | {tot['attribute'][T]} TOGAF; plus {tot['attribute'][I]} institution data (not a standards question) |",
       f"| Within-level rows | {sum(tot['within'].values())} | {tot['within']['grounded']} | {tot['within']['inferred, oracle-confirmed']} | {tot['within']['inferred']} | {tot['within']['inferred, unverified']} |",
       f"| Cross-level rules (50 that can produce a link or report) | {sum(tot['cross'].values())} | {tot['cross']['official']} official | — | {tot['cross']['inferred (no official source)'] + tot['cross']['SDEM definition']} ({tot['cross']['inferred (no official source)']} with no official source, {tot['cross']['SDEM definition']} SDEM definitions) | {tot['cross']['cited, unverified']} |", '']
grounded = tot['definition']['grounded'] + tot['attribute'][B] + tot['attribute'][O] + tot['attribute'][P] + tot['within']['grounded'] + tot['cross']['official']
oracle = tot['within']['inferred, oracle-confirmed']
allitems = sum(tot['definition'].values()) + sum(tot['attribute'].values()) - tot['attribute'][I] + sum(tot['within'].values()) + sum(tot['cross'].values())
out += [f"**Across all four layers** ({allitems} items, institution data excluded): {grounded} grounded ({round(100*grounded/allitems)}%), {oracle} oracle-confirmed ({round(100*oracle/allitems)}%), the rest inferred or gated ({round(100*(allitems-grounded-oracle)/allitems)}%).", '',
        '**Where inference concentrates.** (1) **Cross-level rules**: BIAN publishes almost nothing below A2 and no capability-to-domain mapping, so most rules are SDEM\'s; they are the part tested by the eleven use-case runs (50 rows validated against sealed answers), not by a standard. (2) **Attributes of ArchiMate-derived entities**: ArchiMate defines no attributes, so every A1, A3 and A4 field is either a relationship SDEM chose to record on the entity or a field SDEM defined. (3) **Within-level rows** were mostly inferred, but 113 of them are now confirmed by the Archi oracle.', '',
        '**Where it does not.** A2 is grounded almost entirely in BIAN\'s public material; entity *concepts* are grounded for ' + str(tot['definition']['grounded']) + ' of ' + str(sum(tot['definition'].values())) + ' entities; API attributes follow OpenAPI.', '',
        '## 2. Attribute sources (from metamodel/entity-attributes.json)', '', '| Attribute | Source |', '|---|---|']
out += [f"| `{k}` | {v} |" for k, v in sorted(ATTR_SOURCE.items())]
out += ['', '## 3. Entity by entity', '',
        '| Entity | Standard: concept | Definition | Attributes (source) | Within-level rows | Cross-level rules | Review note |', '|---|---|---|---|---|---|---|']
for t, lvl, std, concept, dc, st, ea, wl, xc, xl in rows:
    a = '; '.join(f"`{k}` {('BIAN' if v == B else 'OpenAPI' if v == O else 'rel.' if v == AR else 'TOGAF' if v == T else 'SDEM' if v == S else 'inst.')}" for k, v in ea.items()) or '—'
    w = ', '.join(f"{n} {k}" for k, n in wl.most_common()) or '—'
    x = (', '.join(f"{n} {k}" for k, n in xc.most_common()) + f" ({', '.join(xl)})") if xl else '—'
    inferred_share = (0 if dc == 'grounded' else 1)
    notes = []
    if dc != 'grounded': notes.append('definition is SDEM\'s' if 'extension' in dc else 'definition interpreted from a standard')
    if any(v == S for v in ea.values()): notes.append('has SDEM-defined fields')
    if xc.get('inferred (no official source)'): notes.append(f"{xc['inferred (no official source)']} cross-level rule(s) with no official source")
    if st == 'pending_release_validation': notes.append('BIAN release not yet verified')
    out.append(f"| `{t}` | {std}: {concept} | {dc} | {a} | {w} | {x} | {'; '.join(notes) or 'grounded'} |")
out += ['', '## 4. What would reduce the inference', '',
        '| Action | Reduces | Needs |', '|---|---|---|',
        '| Verify the 13 BIAN entities and 16 A2 rows against a licensed BIAN release | the `pending_release_validation` status on all of A2 | BIAN membership access |',
        '| Read the ArchiMate 3.2 and TOGAF 10 specifications | the 2 TOGAF rows, the TOGAF attribute, the 7 gated cross-level citations; would upgrade 113 oracle-confirmed rows to specification-verified | a free Open Group account |',
        '| Adopt AsyncAPI for events | adds a public source for `A3.Event` fields | nothing (public standard) |',
        '| A blind test case | tests the inferred cross-level rules on data their author has not seen | a second author |',
        '| Ask BIAN for the unpublished capability-to-domain mapping (B01) | the largest unsourced cross-level rule, S01 | engagement with BIAN |', '']
(R / 'docs' / 'inference-audit.md').write_text('\n'.join(out) + '\n')
print({k: dict(v) for k, v in tot.items()}); print('grounded', grounded, 'oracle', oracle, 'all', allitems)
