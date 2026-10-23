"""SDEM entity metamodel: the A1-A4 entity catalogue, its hierarchy, and within-level relationship rules.

The catalogue is the public vocabulary (metamodel/*.json). It holds no institutional content.
"""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
MM_DIR = ROOT / 'metamodel'
LEVEL_FILES = ['a1-business.json', 'a2-service-domain.json', 'a3-application.json', 'a4-technology.json']


class Metamodel:
    def __init__(self, entities, relationships, version):
        self.entities = {e['type']: e for e in entities}
        self.relationships = relationships
        self.version = version

    @classmethod
    def load(cls, mm_dir=MM_DIR):
        ents, versions = [], set()
        for name in LEVEL_FILES:
            doc = json.loads((Path(mm_dir) / name).read_text(encoding='utf-8'))
            ents += doc['entities']; versions.add(doc['metamodel_version'])
        rels = json.loads((Path(mm_dir) / 'level-relationships.json').read_text(encoding='utf-8'))
        versions.add(rels['metamodel_version'])
        if len(versions) != 1:
            raise ValueError(f'metamodel files disagree on metamodel_version: {sorted(versions)}')
        return cls(ents, rels, versions.pop())

    # ---- hierarchy
    def known(self, t):
        return t in self.entities

    def ancestors(self, t):
        out, cur = [], self.entities.get(t)
        while cur and cur.get('extends'):
            out.append(cur['extends']); cur = self.entities.get(cur['extends'])
        return out

    def is_a(self, t, ancestor):
        return t == ancestor or ancestor in self.ancestors(t)

    def level(self, t):
        e = self.entities.get(t)
        return e['level'] if e else None

    def is_abstract(self, t):
        return bool(self.entities.get(t, {}).get('abstract'))

    def is_artefact(self, t):
        return bool(self.entities.get(t, {}).get('artefact'))

    # ---- within-level relationship rules
    def relationship_issue(self, level, source_type, kind, target_type):
        """Return an issue string if a within-level relationship is not permitted, else None."""
        kinds = {k['kind'] for k in self.relationships['kinds']}
        if kind not in kinds:
            return f'relationship kind {kind!r} is not catalogued'
        for t in (source_type, target_type):
            if not self.known(t):
                return f'entity {t!r} is not in the metamodel'
            if self.level(t) != level:
                return f'entity {t!r} is not an {level} entity'
        if kind == 'association':
            return None  # ArchiMate's generic relationship: permitted between any two entities of one level
        ok = any(c['level'] == level and self.is_a(source_type, c['source_type']) and c['kind'] == kind and self.is_a(target_type, c['target_type'])
                 for c in self.relationships['constraints'])
        if not ok:
            basis = 'BIAN structure' if level == 'A2' else 'ArchiMate 3.2 / TOGAF'
            return f'{level} relationship {source_type} -{kind}-> {target_type} does not match the {basis} constraints (metamodel/level-relationships.json)'
        return None

    # ---- self-check
    def validate(self):
        issues = []
        for t, e in self.entities.items():
            if e['level'] != t.split('.')[0]:
                issues.append(f'{t}: level {e["level"]} does not match prefix')
            p = e.get('extends')
            if p is not None:
                if p not in self.entities:
                    issues.append(f'{t}: extends unknown entity {p!r}')
                elif self.entities[p]['level'] != e['level']:
                    issues.append(f'{t}: extends {p!r} from a different level')
            if e.get('artefact') and e.get('abstract'):
                issues.append(f'{t}: an artefact cannot be abstract')
            if e['definition_source'] == 'bian_reference' and e['evidence_status'] == 'confirmed_in_official_source':
                issues.append(f'{t}: bian_reference entities may only be confirmed through the verification register')
            seen, cur = {t}, p
            while cur:
                if cur in seen:
                    issues.append(f'{t}: extends cycle through {cur!r}'); break
                seen.add(cur); cur = self.entities.get(cur, {}).get('extends')
        for c in self.relationships['constraints']:
            for key in ('source_type', 'target_type'):
                if c[key] not in self.entities:
                    issues.append(f'constraint {c}: unknown entity {c[key]!r}')
        return issues
