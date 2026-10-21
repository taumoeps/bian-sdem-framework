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
