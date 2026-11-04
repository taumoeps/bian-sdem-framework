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
    (r'\bsdmm-engine\b', 'sdem link'), (r'\bsdmm-', 'sdem-'), (r'python -m sdmm\.', 'python -m sdem.'), (r'`sdmm/', '`sdem/'), (r'\bsdmm/', 'sdem/'),
]

# Old command names → the one `sdem <verb>` command (v0.8.0). Applied with TERMS, and alone (apply_commands) to generated
# documents whose prose must not otherwise change — the governing detail spec and the controls register. Records in
# metamodel/ keep their words; only the documents generated from them change.
COMMANDS = [
    (r'(?<![\w./-])sdem-graph (check|build|trace|impact|query|view|baseline|stats)\b', r'sdem \1'),
    (r'(?<![\w./-])sdem-graph\b(?![./-])', 'sdem check'),
    (r'(?<![\w./-])sdem-infer rules\b', 'sdem link'), (r'(?<![\w./-])sdem-infer\b(?![./-])', 'sdem link'),
    (r'(?<![\w./-])sdem-aid\b(?![./-])', 'sdem aid'), (r'(?<![\w./-])sdem-accept\b(?![./-])', 'sdem model accept'),
    (r'(?<![\w./-])sdem-(trace|impact|query|view|matrix|explain|review|approve|home|dashboard|link)\b(?![./-])', r'sdem \1'),
    (r'(?<![\w./-])sdem-validate\b(?![./-])', 'sdem validate'), (r'(?<![\w./-])sdem-diff\b(?![./-])', 'sdem diff'),
    (r'(?<![\w./-])sdem-(structure|relationships|spec|kgspec|catalogue|attributes|logical|physical|controls|metamodel-spec)\b(?![./-])', r'sdem model regenerate (\1)'),
]
TERMS += COMMANDS
_COMPILED = [(re.compile(p), r) for p, r in TERMS]


_COMMANDS = [(re.compile(p), r) for p, r in COMMANDS]


def apply_commands(text):
    for pat, rep in _COMMANDS:
        text = pat.sub(rep, text)
    return text


def apply(text):
    for pat, rep in _COMPILED:
        text = pat.sub(rep, text)
    return text
