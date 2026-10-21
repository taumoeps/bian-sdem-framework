"""BIAN reference adapter interface.

The repository never ships BIAN content. A bank that holds the applicable rights
implements `ReferenceResolver` against its own licensed copy; the validator only
asks whether a canonical identifier exists in a named release.
"""
from dataclasses import dataclass
from typing import Optional, Protocol


@dataclass(frozen=True)
class ReferenceBinding:
    canonical_id: str
    release: str
    entity_type: str
    name: str = ''
    source_record: str = ''


class ReferenceResolver(Protocol):
    def resolve(self, canonical_id: str, release: str) -> Optional[ReferenceBinding]: ...


class NullReferenceResolver:
    """Resolves nothing. Use when no reference repository is attached."""
    def resolve(self, canonical_id, release):
        return None


class StaticReferenceResolver:
    """In-memory resolver for tests and demos. Bindings are supplied by the caller."""
    def __init__(self, bindings):
        self._index = {(b.canonical_id, b.release): b for b in bindings}

    def resolve(self, canonical_id, release):
        return self._index.get((canonical_id, release))


# ---------------------------------------------------------------- level-model entities

@dataclass(frozen=True)
class EntityBinding:
    id: str
    type: str
    version: str


class EntityResolver(Protocol):
    """Looks an entity reference up in the bank's own A1-A4 design models."""
    def resolve_entity(self, id: str, type: str, version: str) -> Optional[EntityBinding]: ...


class CatalogueEntityResolver:
    """File-backed resolver over a plain catalogue of known entities.

    Catalogue shape: {"entities": [{"id": "CAP-310", "type": "L0.BusinessCapability", "versions": ["1.0"]}, ...]}
    A real deployment would replace this with an adapter onto the EA tool, BIAN model and CMDB.
    """
    def __init__(self, catalogue):
        self._index = {}
        for e in catalogue.get('entities', []):
            for v in e.get('versions', []):
                self._index[(e['id'], e['type'], v)] = EntityBinding(e['id'], e['type'], v)

    @classmethod
    def from_file(cls, path):
        import json
        from pathlib import Path
        return cls(json.loads(Path(path).read_text(encoding='utf-8')))

    def resolve_entity(self, id, type, version):
        return self._index.get((id, type, version))
