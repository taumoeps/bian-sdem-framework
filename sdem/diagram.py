"""Render the official-mapping connector diagram (PlantUML) from metamodel/official-mappings.json.

The JSON is the record; the diagram is a projection of it. Only entries whose verification is
'verified' or 'verified_intent_or_target_only' are drawn (B01 is excluded: unpublished).
"""
from pathlib import Path
import argparse, json, sys
from sdem.metamodel import Metamodel, MM_DIR
from sdem.terms import apply as _terms

OFFICIAL = MM_DIR / 'official-mappings.json'
NEW = MM_DIR / 'relationship-rules.json'
# decision → (colour, line style, label) for the new-mappings diagram
DECISION_STYLE = {
    'registry_rule':    ('#1565C0', 'bold',   'registry rule (SDEM relationship type)'),
    'candidate_rule':   ('#2E7D32', '',       'candidate rule (proposed for the registry)'),
    'conditional_rule': ('#EF6C00', '',       'conditional rule (fires on institution data)'),
    'derived_path':     ('#616161', 'dashed', 'derived path (closure over other arrows, never proposed)'),
    'institution_only': ('#6A1B9A', 'dotted', 'institution-only (reported from architecture dataset keys)'),
}
NOT_DRAWN = ('bian_internal', 'not_encodable', 'not_a_mapping', 'historical_method', 'subsumed')
DRAWN = ('verified', 'verified_intent_or_target_only')
LEVEL_NAMES = {'A1': 'A1 Business Architecture', 'A2': 'A2 Service Domain Architecture',
               'A3': 'A3 Application Architecture', 'A4': 'A4 Technology Architecture'}


def load_official(path=OFFICIAL):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def drawn_entries(official):
    return [m for m in official['mappings'] if m['verification'] in DRAWN and m['id'] != 'B01']


def render(official=None, metamodel=None):
    official = official or load_official()
    mm = metamodel or Metamodel.load()
    alias = {t: f"{e['level'].lower()}_{t.split('.')[1].lower()}" for t, e in mm.entities.items()}
    entries = drawn_entries(official)
    b = [m for m in entries if m['tier'] == 'official_bian_only']
    s_solid = [m for m in entries if m['tier'] != 'official_bian_only' and m['verification'] == 'verified']
    s_dashed = [m for m in entries if m['tier'] != 'official_bian_only' and m['verification'] == 'verified_intent_or_target_only']
    out = ['@startuml official-mappings', 'left to right direction',
           'skinparam rectangle {', '  BackgroundColor White', '  BorderColor #424242', '}',
           'skinparam package {', '  BackgroundColor #F5F5F5', '  BorderColor #9E9E9E', '}',
           'skinparam ArrowColor #1565C0', 'skinparam ArrowFontSize 10',
           f"title Official mappings — {len(entries)} verified connectors (B = BIAN-internal, S = cross-level with BIAN guidance)", '']
    for lvl in ('A1', 'A2', 'A3', 'A4'):
        out.append(f'package "{LEVEL_NAMES[lvl]}" as {lvl} {{')
        for t, e in mm.entities.items():
            if e['level'] != lvl:
                continue
            tag = '\\n(artefact)' if e.get('artefact') else '\\n(abstract)' if e.get('abstract') else ''
            out.append(f'  rectangle "{t}{tag}" as {alias[t]}')
        out.append('}'); out.append('')
    out.append(f"' --- B: BIAN's own relationships inside A2 ({len(b)})")
    for m in b:
        out.append(f"{alias[m['source']]} -[#1565C0]-> {alias[m['target']]} : {m['id']} {m['relation']}")
    out.append(''); out.append(f"' --- S: cross-level mappings with BIAN guidance ({len(s_solid)} solid, {len(s_dashed)} dashed = intent/target only)")
    for m in s_solid:
        out.append(f"{alias[m['source']]} -[#2E7D32]-> {alias[m['target']]} : {m['id']} {(m.get('sdem_rule') or m.get('sdmm_rule')) or 'guidance'}")
    for m in s_dashed:
        qual = ' (intent)' if ((m.get('sdem_rule') or m.get('sdmm_rule')) or '') == 'SUPPORTED_BY' else ' (target)'
        out.append(f"{alias[m['source']]} -[#2E7D32,dashed]-> {alias[m['target']]} : {m['id']} {(m.get('sdem_rule') or m.get('sdmm_rule')) or 'guidance'}{qual}")
    out += ['', 'legend right', f'  Blue solid: BIAN-internal (B02–B15, {len(b)})', f'  Green solid: cross-level, BIAN guidance ({len(s_solid)})',
            f'  Green dashed: cross-level, intent/target only ({len(s_dashed)})', 'endlegend', '@enduml']
    return _terms('\n'.join(out) + '\n')


def load_new(path=NEW):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def new_entries(new):
    """Cross-level rows that can become a proposal or a candidate report: every decision with a style."""
    return [m for m in new['mappings'] if m['rule_decision'] in DECISION_STYLE]


def render_new(new=None, metamodel=None):
    """Render metamodel/relationship-rules.puml: every cross-level connection of the plan, labelled with its ID,
    coloured by rule decision. BIAN-internal rows (inside A2) are on the official diagram; rows the plan
    rules out (not a mapping, historical, subsumed, not encodable) are listed in the legend, not drawn."""
    new = new or load_new()
    mm = metamodel or Metamodel.load()
    alias = {t: f"{e['level'].lower()}_{t.split('.')[1].lower()}" for t, e in mm.entities.items()}
    entries = new_entries(new)
    rule_of = {m['id']: (m.get('sdem_rule') or m.get('sdmm_rule')) for m in load_official()['mappings']}
    excluded = [m for m in new['mappings'] if m['rule_decision'] in NOT_DRAWN and m['id'].startswith('S')] + [m for m in new['mappings'] if m['id'] == 'B01']
    ends = {m['source'] for m in entries} | {m['target'] for m in entries}
    def unmapped_reason(t, e):
        if t in ends: return None
        if e.get('artefact'): return 'artefact — never an endpoint'
        rows = [m['id'] for m in new['mappings'] if m['rule_decision'] in NOT_DRAWN and t in (m['source'], m['target'])]
        return ('not a mapping: ' + ', '.join(rows)) if rows else 'no plan row'
    out = ['@startuml relationship-rules', 'left to right direction',
           'skinparam rectangle {', '  BackgroundColor White', '  BorderColor #424242', '}',
           'skinparam package {', '  BackgroundColor #F5F5F5', '  BorderColor #9E9E9E', '}',
           'skinparam ArrowFontSize 9', 'skinparam ArrowThickness 1',
           f"title New mappings (plan) — {len(entries)} cross-level connections by rule decision; every one validated by the use-case suite", '']
    for lvl in ('A1', 'A2', 'A3', 'A4'):
        out.append(f'package "{LEVEL_NAMES[lvl]}" as {lvl} {{')
        for t, e in mm.entities.items():
            if e['level'] != lvl:
                continue
            tag = '\\n(artefact)' if e.get('artefact') else '\\n(abstract)' if e.get('abstract') else ''
            why = unmapped_reason(t, e)
            if why:
                out.append(f'  rectangle "{t}{tag}\\n<size:9><i>no cross-level mapping: {why}</i></size>" as {alias[t]} #EEEEEE')
            else:
                out.append(f'  rectangle "{t}{tag}" as {alias[t]}')
        out.append('}'); out.append('')
    for dec, (colour, style, label) in DECISION_STYLE.items():
        rows = [m for m in entries if m['rule_decision'] == dec]
        out.append(f"' --- {label} ({len(rows)})")
        for m in rows:
            rule = (m.get('sdem_rule') or m.get('sdmm_rule')) or rule_of.get(m['id'])
            text = f"{m['id']} {rule} (step {m.get('fill_step')})" if dec == 'registry_rule' and rule else f"{m['id']} step {m.get('fill_step')} {m.get('confidence', '')}".rstrip()
            spec = f"#{colour.lstrip('#')}" + (f",{style}" if style else '')
            out.append(f"{alias[m['source']]} -[{spec}]-> {alias[m['target']]} : {text}")
        out.append('')
    out += ['legend right']
    for dec, (colour, style, label) in DECISION_STYLE.items():
        n = sum(1 for m in entries if m['rule_decision'] == dec)
        out.append(f"  <color:{colour}>{(style or 'solid').capitalize()}</color>: {label} ({n})")
    out.append("  Grey entity: no cross-level mapping by decision (artefacts are never endpoints; actors and roles are organisation, not mappings)")
    out.append(f"  Not drawn: {', '.join(m['id'] + ' ' + m['rule_decision'].replace('_', ' ') for m in excluded)}; B02–B15 inside A2 are on official-mappings.puml")
    out += ['endlegend', '@enduml']
    return _terms('\n'.join(out) + '\n')


LEVEL_RELS = MM_DIR / 'level-relationships.json'
KIND_STYLE = {'composition': ('#1565C0', ''), 'aggregation': ('#1565C0', 'dashed'), 'realization': ('#2E7D32', 'dashed'), 'assignment': ('#6A1B9A', ''),
              'serving': ('#EF6C00', ''), 'access': ('#616161', 'dotted'), 'flow': ('#EF6C00', 'dashed'), 'triggering': ('#EF6C00', 'dotted'),
              'specialization': ('#424242', ''), 'association': ('#9E9E9E', 'dotted')}


def observed_patterns(examples_dir=None):
    """(level, source_type, kind, target_type) -> count, from every architecture dataset under examples/."""
    import glob
    from collections import Counter
    root = Path(examples_dir) if examples_dir else MM_DIR.parent / 'examples'
    obs = Counter()
    for f in sorted(glob.glob(str(root / '*' / 'a[1-4]-*.json'))):
        d = json.loads(Path(f).read_text(encoding='utf-8')); t = {i['id']: i['type'] for i in d['instances']}
        for r in d['relationships']:
            if r['source'] in t and r['target'] in t:
                obs[(d['level'], t[r['source']], r['kind'], t[r['target']])] += 1
    return obs


def render_levels(metamodel=None, level_rels=None, examples_dir=None):
    """Render metamodel/level-relationships.puml: the within-level structure of each architecture.
    A2 is drawn from the BIAN-fixed constraint set in level-relationships.json; A1, A3 and A4 from the
    relationship patterns observed across the example architecture datasets (the institution's own structure, using
    catalogued ArchiMate kinds) — observed, not prescribed."""
    mm = metamodel or Metamodel.load()
    lr = level_rels or json.loads(LEVEL_RELS.read_text(encoding='utf-8'))
    alias = {t: f"{e['level'].lower()}_{t.split('.')[1].lower()}" for t, e in mm.entities.items()}
    a2 = [(c['source_type'], c['kind'], c['target_type']) for c in lr['constraints'] if c['level'] == 'A2']
    obs = observed_patterns(examples_dir)
    out = ['@startuml level-relationships', 'left to right direction',
           'skinparam rectangle {', '  BackgroundColor White', '  BorderColor #424242', '}',
           'skinparam package {', '  BackgroundColor #F5F5F5', '  BorderColor #9E9E9E', '}', 'skinparam ArrowFontSize 9',
           'title Within-level structure — every level from its reference architecture: A2 BIAN; A1, A3, A4 ArchiMate 3.2 / TOGAF (association permitted everywhere, not drawn)', '']
    rows_by_level = {l: [(c['source_type'], c['kind'], c['target_type'], c.get('id', '')) for c in lr['constraints'] if c['level'] == l] for l in ('A1', 'A2', 'A3', 'A4')}
    for lvl in ('A1', 'A2', 'A3', 'A4'):
        out.append(f'package "{LEVEL_NAMES[lvl]}" as {lvl} {{')
        for t, e in mm.entities.items():
            if e['level'] != lvl: continue
            tag = '\\n(artefact)' if e.get('artefact') else '\\n(abstract)' if e.get('abstract') else ''
            out.append(f'  rectangle "{t}{tag}" as {alias[t]}')
        src = {'A1': 'ArchiMate 3.2 ch. 6–8', 'A2': 'BIAN Service Landscape metamodel', 'A3': 'ArchiMate 3.2 ch. 9; TOGAF (SBB)', 'A4': 'ArchiMate 3.2 ch. 10'}[lvl]
        out.append(f"  ' constraints from {src} ({len(rows_by_level[lvl])})")
        for s_, k, t_, rid in rows_by_level[lvl]:
            c, st = KIND_STYLE[k]; out.append(f"  {alias[s_]} -[#{c.lstrip('#')}{',' + st if st else ''}]-> {alias[t_]} : {rid} {k}")
        ext = [(t, e['extends']) for t, e in mm.entities.items() if e['level'] == lvl and e.get('extends')]
        if ext:
            out.append(f"  ' catalogue inheritance — entity extends parent (is-a; ArchiMate specialization) ({len(ext)})")
            for t, parent in ext:
                out.append(f"  {alias[t]} -[#424242]-|> {alias[parent]} : extends")
        out.append('}'); out.append('')
    out += ['legend right', '  Kinds (ArchiMate 3.2): composition solid blue, aggregation dashed blue, realization dashed green, assignment purple,',
            '  serving orange, flow dashed orange, triggering dotted orange, access dotted grey; association is permitted between any two entities of one level and is not drawn',
            '  Every arrow is a constraint row in metamodel/level-relationships.json (ID shown; full table in docs/relationships-planning.md); sdem-graph check rejects any other within-level relationship.',
            '  Hollow-headed black arrows: catalogue inheritance (extends). A4.InfrastructureComponent is abstract — never instantiated; it is the DEPLOYED_ON target type and every concrete A4 entity is-a InfrastructureComponent.',
            '  A2 from BIAN (public portal); A1, A3, A4 paraphrased from ArchiMate 3.2 / TOGAF 10 chapter structure (login-gated, unverified) for the concept each entity derives from.',
            'endlegend', '@enduml']
    return _terms('\n'.join(out) + '\n')


def render_merged(new=None, metamodel=None, level_rels=None, examples_dir=None):
    """Render metamodel/merged-relationships.puml: the within-level structure (as level-relationships.puml) and
    every cross-level plan connection (as relationship-rules.puml) on one canvas. Within-level arrows are thin
    and unlabelled by ID; cross-level arrows carry their plan ID and decision colour."""
    new = new or load_new()
    mm = metamodel or Metamodel.load()
    lr = level_rels or json.loads(LEVEL_RELS.read_text(encoding='utf-8'))
    alias = {t: f"{e['level'].lower()}_{t.split('.')[1].lower()}" for t, e in mm.entities.items()}
    entries = new_entries(new)
    rule_of = {m['id']: (m.get('sdem_rule') or m.get('sdmm_rule')) for m in load_official()['mappings']}
    ends = {m['source'] for m in entries} | {m['target'] for m in entries}
    rows_by_level = {l: [(c['source_type'], c['kind'], c['target_type'], c.get('id', '')) for c in lr['constraints'] if c['level'] == l] for l in ('A1', 'A2', 'A3', 'A4')}
    within = sum(len(v) for v in rows_by_level.values())
    out = ['@startuml merged-relationships', 'left to right direction',
           'skinparam rectangle {', '  BackgroundColor White', '  BorderColor #424242', '}',
           'skinparam package {', '  BackgroundColor #F5F5F5', '  BorderColor #9E9E9E', '}', 'skinparam ArrowFontSize 9',
           f"title Merged view — {within} within-level links (thin, kind only) and {len(entries)} cross-level mappings (plan ID, coloured by decision)", '']
    for lvl in ('A1', 'A2', 'A3', 'A4'):
        out.append(f'package "{LEVEL_NAMES[lvl]}" as {lvl} {{')
        for t, e in mm.entities.items():
            if e['level'] != lvl: continue
            tag = '\\n(artefact)' if e.get('artefact') else '\\n(abstract)' if e.get('abstract') else ''
            if t in ends: out.append(f'  rectangle "{t}{tag}" as {alias[t]}')
            else: out.append(f'  rectangle "{t}{tag}" as {alias[t]} #EEEEEE')
        out.append(f"  ' within {lvl} — constraint rows ({len(rows_by_level[lvl])})")
        for s_, k, t_, rid in rows_by_level[lvl]:
            out.append(f"  {alias[s_]} -[#B0BEC5]-> {alias[t_]} : <size:8>{rid} {k}</size>")
        out.append('}'); out.append('')
    for dec, (colour, style, label) in DECISION_STYLE.items():
        rows = [m for m in entries if m['rule_decision'] == dec]
        out.append(f"' --- cross-level: {label} ({len(rows)})")
        for m in rows:
            rule = (m.get('sdem_rule') or m.get('sdmm_rule')) or rule_of.get(m['id'])
            text = f"{m['id']} {rule}" if dec == 'registry_rule' and rule else f"{m['id']}"
            spec = f"#{colour.lstrip('#')}" + (f",{style}" if style else '')
            out.append(f"{alias[m['source']]} -[{spec}]-> {alias[m['target']]} : {text}")
        out.append('')
    out += ['legend right', '  Light grey thin arrows: within-level constraint rows (ArchiMate kind as label) — A2 from BIAN; A1, A3, A4 from ArchiMate 3.2 / TOGAF']
    for dec, (colour, style, label) in DECISION_STYLE.items():
        n = sum(1 for m in entries if m['rule_decision'] == dec)
        out.append(f"  <color:{colour}>{(style or 'solid').capitalize()}</color>: cross-level {label} ({n})")
    out += ['  Grey entity: no cross-level mapping by decision', '  Detail: official-mappings.puml, relationship-rules.puml, level-relationships.puml', 'endlegend', '@enduml']
    return _terms('\n'.join(out) + '\n')


def main(argv=None):
    parser = argparse.ArgumentParser(prog='sdem-diagram', description='Render metamodel/official-mappings.puml and metamodel/relationship-rules.puml from their JSON records.')
    parser.add_argument('--which', choices=['official', 'new', 'levels', 'merged', 'both', 'all'], default='all')
    parser.add_argument('--check', action='store_true', help='exit 1 if a committed file differs from the rendered output')
    args = parser.parse_args(argv)
    jobs = {'official': (MM_DIR / 'official-mappings.puml', render), 'new': (MM_DIR / 'relationship-rules.puml', render_new), 'levels': (MM_DIR / 'level-relationships.puml', render_levels), 'merged': (MM_DIR / 'merged-relationships.puml', render_merged)}
    rc = 0
    for name in ({'both': ['official', 'new'], 'all': ['official', 'new', 'levels', 'merged']}.get(args.which, [args.which])):
        out, fn = jobs[name]; text = fn()
        if args.check:
            current = out.read_text(encoding='utf-8') if out.exists() else ''
            ok = current == text; rc |= 0 if ok else 1
            print(f"{out.name}: {'up to date' if ok else 'STALE: regenerate with python -m sdem.diagram'}")
        else:
            out.write_text(text, encoding='utf-8'); print(f'wrote {out}')
    return rc


if __name__ == '__main__':
    raise SystemExit(main())
