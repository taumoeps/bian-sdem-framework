"""SDEM terminology — one ordered set of replacements applied to every generated document and diagram.

Order matters: the old word "registry" (the nine relationship types) becomes the *relationship type catalogue*
before the old "mapping set" becomes the *relationship registry*, so the two never collide. Persisted identifiers
(`registry_version`, `mapping_id`, the `registry_rule` decision value, file names such as `mappings.json`) are
not prose and are left alone: every replacement below is a phrase, never a bare identifier.
"""
import re

# (pattern, replacement) — regular expressions, applied in order
TERMS = [
    (r'\bBIAN Service Domain Mapping Model\b', 'Service Domain Enterprise Metamodel'),
    (r'\bService Domain Mapping Model\b', 'Service Domain Enterprise Metamodel'),
    (r'\bSDMM\b', 'SDEM'),
    # the nine relationship types: "registry" → relationship type catalogue
    (r'\bnine registry relationships\b', 'nine catalogued relationship types'),
    (r'\bregistry relationships\b', 'catalogued relationship types'),
    (r'\bregistry rules\b', 'catalogue rules'), (r'\bRegistry rules\b', 'Catalogue rules'),
    (r'\bregistry rule\b', 'catalogue rule'), (r'\bRegistry rule\b', 'Catalogue rule'),
    (r'\bregistry proposals\b', 'catalogue-typed proposals'),
    (r'\bThe registry\b', 'The relationship type catalogue'), (r'\bthe registry\b', 'the relationship type catalogue'),
    (r'\bRegistry: kinds of link\b', 'Relationship type catalogue: kinds of link'),
    # the links: mapping set → Architecture Relationship Registry
    (r'\bMapping-set records\b', 'Relationship registry records'),
    (r'\bmapping-set records\b', 'relationship registry records'), (r'\bmapping-set record\b', 'relationship registry record'),
    (r'\bmapping-set\b', 'relationship-registry'),
    (r'\bMapping sets\b', 'Relationship registries'), (r'\bmapping sets\b', 'relationship registries'),
    (r'\bMapping set\b', 'Relationship registry'), (r'\bmapping set\b', 'relationship registry'),
    (r'\bmapping documents\b', 'relationship registries'), (r'\bmapping document\b', 'relationship registry'),
    # the program: mapping engine → Architecture Relationship Inference Engine
    (r'\bMapping engine\b', 'Inference engine'), (r'\bmapping engine\b', 'inference engine'), (r'\bMapping Engine\b', 'Inference Engine'),
    # the rules: mapping model → Architecture Relationship Rules Model
    (r'\bMapping model\b', 'Relationship rules model'), (r'\bmapping model\b', 'relationship rules model'),
    (r'\bmapping-model\b', 'relationship-rules'),
    # graphs
    (r'\bFederated graph\b', 'Federated knowledge graph'), (r'\bfederated graph\b', 'federated knowledge graph'),
    (r'\bLocal graphs\b', 'Local knowledge graphs'), (r'\blocal graphs\b', 'local knowledge graphs'),
    (r'\bLocal graph\b', 'Local knowledge graph'), (r'\blocal graph\b', 'local knowledge graph'),
    (r'\bknowledge knowledge graph', 'knowledge graph'),
    # commands
    (r'\bsdmm-engine\b', 'sdem-infer'), (r'\bsdmm-', 'sdem-'), (r'python -m sdmm\.', 'python -m sdem.'), (r'`sdmm/', '`sdem/'), (r'\bsdmm/', 'sdem/'),
]
_COMPILED = [(re.compile(p), r) for p, r in TERMS]


def apply(text):
    for pat, rep in _COMPILED:
        text = pat.sub(rep, text)
    return text
