"""A test workspace's layer files, whichever form it is in (DL-10): SDEM 0.19's names (a1-business.json …) in a workspace that has
not been migrated, the layer ids (business.json …) in one in SDEM 0.20's form — which `sdem new` makes when SDEM_FORM is 0.20 (DL-D9a).
A test names a layer by its id (ST-01), which means the same layer in either form."""
import json
from pathlib import Path

OLD = {'business': 'a1-business.json', 'bian': 'a2-service-domain.json', 'data': 'a3-application.json',
       'application': 'a3-application.json', 'technology': 'a4-technology.json'}


def migrated(ws):
    """The workspace is in SDEM 0.20's form."""
    try: return json.loads((Path(ws) / 'workspace.json').read_text(encoding='utf-8')).get('names') == 'ids'
    except (OSError, ValueError): return False


def lf(ws, layer_id):
    """The file that holds a layer's records — Data's records are in the Application file until a workspace is migrated."""
    ws = Path(ws)
    return ws / (f'{layer_id}.json' if migrated(ws) else OLD[layer_id])
