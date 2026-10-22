"""Render the official-mapping connector diagram (PlantUML) from metamodel/official-mappings.json.

The JSON is the record; the diagram is a projection of it. Only entries whose verification is
'verified' or 'verified_intent_or_target_only' are drawn (B01 is excluded: unpublished).
"""
from pathlib import Path
import argparse, json, sys
from sdmm.metamodel import Metamodel, MM_DIR

OFFICIAL = MM_DIR / 'official-mappings.json'
NEW = MM_DIR / 'new-mappings.json'
# decision → (colour, line style, label) for the new-mappings diagram
DECISION_STYLE = {
    'registry_rule':    ('#1565C0', 'bold',   'registry rule (SDMM relationship type)'),
    'candidate_rule':   ('#2E7D32', '',       'candidate rule (proposed for the registry)'),
    'conditional_rule': ('#EF6C00', '',       'conditional rule (fires on institution data)'),
    'derived_path':     ('#616161', 'dashed', 'derived path (closure over other arrows, never proposed)'),
    'institution_only': ('#6A1B9A', 'dotted', 'institution-only (reported from export keys)'),
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
        out.append(f"{alias[m['source']]} -[#2E7D32]-> {alias[m['target']]} : {m['id']} {m.get('sdmm_rule') or 'guidance'}")
    for m in s_dashed:
        qual = ' (intent)' if (m.get('sdmm_rule') or '') == 'SUPPORTED_BY' else ' (target)'
        out.append(f"{alias[m['source']]} -[#2E7D32,dashed]-> {alias[m['target']]} : {m['id']} {m.get('sdmm_rule') or 'guidance'}{qual}")
    out += ['', 'legend right', f'  Blue solid: BIAN-internal (B02–B15, {len(b)})', f'  Green solid: cross-level, BIAN guidance ({len(s_solid)})',
            f'  Green dashed: cross-level, intent/target only ({len(s_dashed)})', 'endlegend', '@enduml']
    return '\n'.join(out) + '\n'


def load_new(path=NEW):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def new_entries(new):
    """Cross-level rows that can become a proposal or a candidate report: every decision with a style."""
    return [m for m in new['mappings'] if m['rule_decision'] in DECISION_STYLE]


def render_new(new=None, metamodel=None):
    """Render metamodel/new-mappings.puml: every cross-level connection of the plan, labelled with its ID,
    coloured by rule decision. BIAN-internal rows (inside A2) are on the official diagram; rows the plan
    rules out (not a mapping, historical, subsumed, not encodable) are listed in the legend, not drawn."""
    new = new or load_new()
    mm = metamodel or Metamodel.load()
    alias = {t: f"{e['level'].lower()}_{t.split('.')[1].lower()}" for t, e in mm.entities.items()}
    entries = new_entries(new)
    rule_of = {m['id']: m.get('sdmm_rule') for m in load_official()['mappings']}
    excluded = [m for m in new['mappings'] if m['rule_decision'] in NOT_DRAWN and m['id'].startswith('S')] + [m for m in new['mappings'] if m['id'] == 'B01']
    out = ['@startuml new-mappings', 'left to right direction',
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
            out.append(f'  rectangle "{t}{tag}" as {alias[t]}')
        out.append('}'); out.append('')
    for dec, (colour, style, label) in DECISION_STYLE.items():
        rows = [m for m in entries if m['rule_decision'] == dec]
        out.append(f"' --- {label} ({len(rows)})")
        for m in rows:
            rule = m.get('sdmm_rule') or rule_of.get(m['id'])
            text = f"{m['id']} {rule} (step {m.get('fill_step')})" if dec == 'registry_rule' and rule else f"{m['id']} step {m.get('fill_step')} {m.get('confidence', '')}".rstrip()
            spec = f"#{colour.lstrip('#')}" + (f",{style}" if style else '')
            out.append(f"{alias[m['source']]} -[{spec}]-> {alias[m['target']]} : {text}")
        out.append('')
    out += ['legend right']
    for dec, (colour, style, label) in DECISION_STYLE.items():
        n = sum(1 for m in entries if m['rule_decision'] == dec)
        out.append(f"  <color:{colour}>{(style or 'solid').capitalize()}</color>: {label} ({n})")
    out.append(f"  Not drawn: {', '.join(m['id'] + ' ' + m['rule_decision'].replace('_', ' ') for m in excluded)}; B02–B15 inside A2 are on official-mappings.puml")
    out += ['endlegend', '@enduml']
    return '\n'.join(out) + '\n'


def main(argv=None):
    parser = argparse.ArgumentParser(prog='sdmm-diagram', description='Render metamodel/official-mappings.puml and metamodel/new-mappings.puml from their JSON records.')
    parser.add_argument('--which', choices=['official', 'new', 'both'], default='both')
    parser.add_argument('--check', action='store_true', help='exit 1 if a committed file differs from the rendered output')
    args = parser.parse_args(argv)
    jobs = {'official': (MM_DIR / 'official-mappings.puml', render), 'new': (MM_DIR / 'new-mappings.puml', render_new)}
    rc = 0
    for name in (['official', 'new'] if args.which == 'both' else [args.which]):
        out, fn = jobs[name]; text = fn()
        if args.check:
            current = out.read_text(encoding='utf-8') if out.exists() else ''
            ok = current == text; rc |= 0 if ok else 1
            print(f"{out.name}: {'up to date' if ok else 'STALE: regenerate with python -m sdmm.diagram'}")
        else:
            out.write_text(text, encoding='utf-8'); print(f'wrote {out}')
    return rc


if __name__ == '__main__':
    raise SystemExit(main())
