"""AID carries the information model (metamodel 0.15.0; docs/design/sdem-full-design-metamodel-design.md IM-10).

AID-I01  For each A2 business object the workspace holds with typed field records (sdem bian import --objects, or written by a person)
         and no data entity mapped to it yet: an A3 data entity, marked inferred, with one A3 data attribute per field — its physical type
         from a fixed table (TYPES), required as the field is, the identifier as the primary key.
AID-I02  A field that refers to another business object becomes a foreign key to that object's data entity (inferred here, or already
         mapped) — an association, marked inferred.
AID-I03  The links between layers are proposed, never approved: MAPPED_TO (business object → data entity) and FIELD_MAPPED_TO (each
         BIAN attribute → its data attribute), confidence low — a person approves them with data_model evidence.
AID-I04  Only what a person wrote or confirmed is read (AID-W08); a rejected record is never inferred again.
AID-I08  Where the workspace has applications, a table is inferred for a BIAN object only when one of them realises (approved or proposed) the
         service domain whose control record works on the object — otherwise nothing here would store it, and SDEM says so instead (found in the
         public twin's first run, F4: a 27-field table for Party Authentication that the design never had).
"""
from .identity import T as _T, layer as _L  # ST-01…ST-05: layers and types by id (docs/design/sdem-stable-identity-spec.md)
import re











def propose_information(*a, **k):   # 0.22 step 3c: AID-I01…I04 are BIAN's (sdem/aid_bian.py) — here for those who call them from aid_info
    from .aid_bian import propose_information as f
    return f(*a, **k)


def propose_access(*a, **k):   # AID-I07, likewise
    from .aid_bian import propose_access as f
    return f(*a, **k)
