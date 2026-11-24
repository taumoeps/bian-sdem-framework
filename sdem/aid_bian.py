"""BIAN's part of AID (`sdem aid`) — the 0.22 plan, step 3c: the four points where AID's inference goes through BIAN, called by
sdem/aid_fill.py at the same points, in the same order, so they can move to the sdem-bian extension (R-D5) behind a phased contract.

    projection     AID-F1…F3, R1…R3, M: the domains, BIAN's container pattern, the reverse steps (aid.project, with BIAN's catalogue)
    patterns       AID-D05: a BIAN domain a pattern names and the design lacks
    information    AID-K02, I01…I04, I07: BIAN objects and the tables that store them
    direct         AID-L01…L05, I05, K01: links that go through BIAN's service domains, objects and fields
"""
from .identity import layer as _L  # ST-01…ST-05: layers by id

CORE_DIRECT = {'AID-L06', 'AID-I06'}


def projection(ws, have, registry):
    """(the projection package, the catalogue it used) — WS-01: the workspace's own BIAN layer plus the BIAN catalogue it uses."""
    from .aid import project
    from .new import catalogue as workspace_catalogue
    catalogue = workspace_catalogue(ws)
    return project(have, catalogue, registry, either=True), catalogue   # AID-M02: for a person to review, keep what either side supports


def pattern_domains(after, catalogue, maps, mm, structs, dmark, rejected):
    from .aid_complete import pattern_domains as f
    return f(after, catalogue, maps, mm, structs, dmark, rejected)


def match_existing(after, maps, mm):
    from .aid_links import match_existing as f
    return f(after, maps, mm)


def propose_information(bian_doc, a3doc, maps, mark, rejected, unconfirmed):
    from .aid_info import propose_information as f
    return f(bian_doc, a3doc, maps, mark, rejected, unconfirmed)


def propose_access(after, maps, mm, mark):
    from .aid_info import propose_access as f
    return f(after, maps, mm, mark)


def direct(after, maps, mm):
    """BIAN's rules of AID-L01…L05, I05 (propose_direct), then K01 (propose_fields)."""
    from .aid_links import propose_direct, propose_fields, BIAN_DIRECT
    return propose_direct(after, maps, mm, only=BIAN_DIRECT), propose_fields(after, maps, mm)
