"""Render the official-mapping connector diagram (PlantUML) from metamodel/official-mappings.json.

The JSON is the record; the diagram is a projection of it. Only entries whose verification is
'verified' or 'verified_intent_or_target_only' are drawn (B01 is excluded: unpublished).
"""
from pathlib import Path
import argparse, json, sys
from sdmm.metamodel import Metamodel, MM_DIR

OFFICIAL = MM_DIR / 'official-mappings.json'
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


def main(argv=None):
    parser = argparse.ArgumentParser(prog='sdmm-diagram', description='Render metamodel/official-mappings.puml from official-mappings.json.')
    parser.add_argument('--out', default=str(MM_DIR / 'official-mappings.puml'))
    parser.add_argument('--check', action='store_true', help='exit 1 if the committed file differs from the rendered output')
    args = parser.parse_args(argv)
    text = render()
    if args.check:
        current = Path(args.out).read_text(encoding='utf-8') if Path(args.out).exists() else ''
        print('up to date' if current == text else 'STALE: regenerate with python -m sdmm.diagram')
        return 0 if current == text else 1
    Path(args.out).write_text(text, encoding='utf-8'); print(f'wrote {args.out}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
