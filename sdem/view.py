"""Self-contained HTML view of a graph store (docs/graph-store-spec.md §10, GS-V-01…03).

One file: data, script and style inline, no network access. Four horizontal bands A1 (top) … A4 (bottom); within-level
links inside a band, approved cross-level links between bands. Click a record for its details and links; filter by
architecture and type; highlight a record's trace down (towards A4) or up (towards A1).
"""
import html, json
from pathlib import Path

from .store import GraphReader

LEVELS = ('A1', 'A2', 'A3', 'A4')
NAMES = {'A1': 'A1 Business', 'A2': 'A2 Service Domain (BIAN)', 'A3': 'A3 Application', 'A4': 'A4 Technology'}
BOX_W, BOX_H, STEP_X, STEP_Y, PAD_X, BAND_GAP, PER_ROW = 168, 38, 184, 56, 170, 46, 8


def layout(reader):
    """Deterministic positions: per band, records grouped by entity type in catalogue order, wrapped PER_ROW to a row."""
    order = {t: n for n, t in enumerate(reader.mm.entities)}
    nodes, bands, y = [], [], 30
    for lvl in LEVELS:
        recs = sorted(reader.nodes(level=lvl), key=lambda r: (order.get(r['type'], 999), r['id']))
        if not recs: continue
        rows = (len(recs) + PER_ROW - 1) // PER_ROW; top = y
        for n, r in enumerate(recs):
            nodes.append({'k': r['key'], 'id': r['id'], 'v': r['version'], 'name': r['name'], 'type': r['type'], 'lvl': lvl,
                          'x': PAD_X + (n % PER_ROW) * STEP_X, 'y': y + 26 + (n // PER_ROW) * STEP_Y,
                          'meta': {k: r[k] for k in ('lifecycle_status', 'canonical_id', 'description', 'definition_uri') if k in r}, 'attrs': r.get('attributes', {})})
        h = 26 + rows * STEP_Y; bands.append({'lvl': lvl, 'label': NAMES[lvl], 'y': top, 'h': h}); y += h + BAND_GAP
    keyof = {(n['lvl'], n['id']): n['k'] for n in nodes}
    edges = [{'s': keyof[(e['level'], e['source'])], 't': keyof[(e['level'], e['target'])], 'rel': e['kind'], 'scope': 'w'}
             for e in reader.edges('within-level') if (e['level'], e['source']) in keyof and (e['level'], e['target']) in keyof]
    for e in reader.edges('cross-level'):
        s = reader.node(reader.mm.level(e['source']['type']) or '', e['source']['id'], e['source']['version'])
        t = reader.node(reader.mm.level(e['target']['type']) or '', e['target']['id'], e['target']['version'])
        if s and t: edges.append({'s': s['key'], 't': t['key'], 'rel': e['relationship'], 'scope': 'x', 'mid': e['mapping_id']})
    return {'nodes': nodes, 'edges': edges, 'bands': bands, 'width': PAD_X + PER_ROW * STEP_X, 'height': y, 'box': [BOX_W, BOX_H]}


def render(store, title=None):
    reader = GraphReader.from_store(store)
    data = layout(reader); b = reader.baseline()
    data['baseline'] = f"build {b['build']} · " + ' · '.join(f'{k} {v}' for k, v in b['levels'].items())
    title = title or f'SDEM graph — {Path(store).resolve().parent.name if Path(store).name == "graph" else Path(store).name}'
    return PAGE.replace('__TITLE__', html.escape(title)).replace('__DATA__', json.dumps(data, ensure_ascii=False).replace('</', '<\\/'))


def write(store, out=None, title=None):
    out = Path(out) if out else Path(store) / 'view.html'
    out.write_text(render(store, title), encoding='utf-8'); return out


PAGE = r'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<style>
:root{--bg:#fbfaf7;--fg:#1d1d1b;--muted:#6b6a65;--line:#d8d5cc;--panel:#ffffff;--a1:#b5651d;--a2:#2f6f9f;--a3:#4f7f3a;--a4:#7a4f9a;--x:#c2410c;--hl:#e11d48;--band:#f2efe8}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#161614;--fg:#ecebe6;--muted:#a19f97;--line:#3a3934;--panel:#1f1f1c;--band:#22211e;--a1:#e0995a;--a2:#6fa8d6;--a3:#8dbd73;--a4:#b98fd8;--x:#fb923c;--hl:#fb7185}}
:root[data-theme="dark"]{--bg:#161614;--fg:#ecebe6;--muted:#a19f97;--line:#3a3934;--panel:#1f1f1c;--band:#22211e;--a1:#e0995a;--a2:#6fa8d6;--a3:#8dbd73;--a4:#b98fd8;--x:#fb923c;--hl:#fb7185}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:14px/1.45 system-ui,-apple-system,"Segoe UI",sans-serif}
header{padding:12px 16px;border-bottom:1px solid var(--line);display:flex;flex-wrap:wrap;gap:8px 16px;align-items:center}
h1{font-size:16px;margin:0 12px 0 0}.muted{color:var(--muted);font-size:12px}
.controls{display:flex;flex-wrap:wrap;gap:6px 12px;align-items:center}label{font-size:13px;white-space:nowrap}
select,button{font:inherit;font-size:13px;padding:3px 8px;border:1px solid var(--line);border-radius:6px;background:var(--panel);color:var(--fg)}
main{display:flex;flex-wrap:wrap;gap:0}#canvas{flex:1 1 640px;min-width:0;overflow:auto;height:calc(100vh - 110px)}
aside{flex:0 1 340px;min-width:260px;border-left:1px solid var(--line);padding:12px 16px;overflow:auto;height:calc(100vh - 110px);background:var(--panel)}
@media (max-width:760px){#canvas{height:60vh;flex-basis:100%}aside{flex-basis:100%;border-left:0;border-top:1px solid var(--line);height:auto}}
svg text{fill:var(--fg);font-size:11px}.band{fill:var(--band)}.bandlbl{font-size:13px;font-weight:600;fill:var(--muted)}
.node rect{fill:var(--panel);stroke-width:1.5}.node{cursor:pointer}.node.dim{opacity:.18}.node.sel rect{stroke:var(--hl);stroke-width:3}.node.hl rect{stroke:var(--hl);stroke-width:2.2}
.e{fill:none;stroke-width:1}.e.w{stroke:var(--line)}.e.x{stroke:var(--x);stroke-width:1.4;opacity:.75}.e.dim{opacity:.06}.e.hl{stroke:var(--hl);stroke-width:2.4;opacity:1}
table{border-collapse:collapse;width:100%;font-size:12px}td{border-top:1px solid var(--line);padding:3px 4px;vertical-align:top;word-break:break-word}td:first-child{color:var(--muted);width:38%}
h2{font-size:14px;margin:4px 0}h3{font-size:12px;margin:12px 0 4px;color:var(--muted);text-transform:uppercase;letter-spacing:.04em}
ul{margin:0;padding-left:16px;font-size:12px}a.lnk{color:var(--a2);cursor:pointer;text-decoration:underline}
</style></head><body>
<header><h1>__TITLE__</h1><span class="muted" id="base"></span>
<div class="controls"><span id="lvls"></span>
<label>Type <select id="type"><option value="">all</option></select></label>
<label>Trace <select id="dir"><option value="">off</option><option value="down">down (towards A4)</option><option value="up">up (towards A1)</option></select></label>
<label><input type="checkbox" id="comp"> follow part–whole</label>
<button id="zin" aria-label="Zoom in">+</button><button id="zout" aria-label="Zoom out">−</button>
<button id="theme" aria-label="Toggle theme">◐</button></div></header>
<main><div id="canvas"></div><aside id="side"><p class="muted">Click a record to see its details and links. Orange lines are approved cross-architecture links; grey lines are links inside an architecture.</p></aside></main>
<script>
const D=__DATA__;const NS="http://www.w3.org/2000/svg";const col={A1:"var(--a1)",A2:"var(--a2)",A3:"var(--a3)",A4:"var(--a4)"};
const byK={};D.nodes.forEach(n=>byK[n.k]=n);let zoom=1,sel=null;const show={A1:1,A2:1,A3:1,A4:1};
document.getElementById("base").textContent=D.baseline;
const svg=document.createElementNS(NS,"svg");svg.setAttribute("viewBox",`0 0 ${D.width} ${D.height}`);
function size(){svg.setAttribute("width",D.width*zoom);svg.setAttribute("height",D.height*zoom)}size();
document.getElementById("canvas").appendChild(svg);
function el(t,a,p){const e=document.createElementNS(NS,t);for(const k in a)e.setAttribute(k,a[k]);(p||svg).appendChild(e);return e}
D.bands.forEach(b=>{el("rect",{class:"band",x:8,y:b.y,width:D.width-16,height:b.h,rx:8});const t=el("text",{class:"bandlbl",x:20,y:b.y+20});t.textContent=b.label});
const [W,H]=D.box;const eg=el("g",{});const ng=el("g",{});
D.edges.forEach(e=>{const s=byK[e.s],t=byK[e.t];let d;
 if(e.scope==="w"&&s.y===t.y){const m=Math.min(s.y,t.y)-14;d=`M${s.x+W/2},${s.y} C${s.x+W/2},${m} ${t.x+W/2},${m} ${t.x+W/2},${t.y}`}
 else{const [a,b]=s.y<=t.y?[s,t]:[t,s];d=`M${a.x+W/2},${a.y+H} C${a.x+W/2},${(a.y+H+b.y)/2} ${b.x+W/2},${(a.y+H+b.y)/2} ${b.x+W/2},${b.y}`}
 e.el=el("path",{d,class:"e "+e.scope},eg);const ti=el("title",{},e.el);ti.textContent=(e.mid?e.mid+" ":"")+e.rel});
D.nodes.forEach(n=>{const g=el("g",{class:"node",transform:`translate(${n.x},${n.y})`,tabindex:0},ng);n.el=g;
 el("rect",{width:W,height:H,rx:6,stroke:col[n.lvl]},g);const t1=el("text",{x:8,y:15},g);t1.textContent=n.name.length>24?n.name.slice(0,23)+"…":n.name;
 const t2=el("text",{x:8,y:29,style:"fill:var(--muted);font-size:10px"},g);const sub=n.type.split(".")[1]+" · "+n.id;t2.textContent=sub.length>30?sub.slice(0,29)+"…":sub;
 const ti=el("title",{},g);ti.textContent=n.name+"\n"+n.type+" "+n.id+"@"+n.v;
 g.addEventListener("click",()=>pick(n));g.addEventListener("keydown",ev=>{if(ev.key==="Enter")pick(n)})});
const types=[...new Set(D.nodes.map(n=>n.type))].sort();const ts=document.getElementById("type");types.forEach(t=>{const o=document.createElement("option");o.value=o.textContent=t;ts.appendChild(o)});
const lv=document.getElementById("lvls");["A1","A2","A3","A4"].forEach(l=>{if(!D.bands.some(b=>b.lvl===l))return;const lab=document.createElement("label");lab.innerHTML=`<input type="checkbox" checked> ${l}`;lab.firstChild.onchange=ev=>{show[l]=ev.target.checked?1:0;paint()};lv.appendChild(lab)});
function trace(start,dir,comp){const seen=new Set([start]),es=new Set(),q=[start];while(q.length){const k=q.pop();D.edges.forEach(e=>{
  let a,b;if(e.scope==="x"){[a,b]=dir==="down"?[e.s,e.t]:[e.t,e.s]}else if(comp&&(e.rel==="composition"||e.rel==="aggregation")){[a,b]=dir==="down"?[e.t,e.s]:[e.s,e.t]}else return;
  if(a===k){es.add(e);if(!seen.has(b)){seen.add(b);q.push(b)}}})}return{seen,es}}
function paint(){const t=ts.value,dir=document.getElementById("dir").value,comp=document.getElementById("comp").checked;
 const tr=sel&&dir?trace(sel.k,dir,comp):null;
 D.nodes.forEach(n=>{const vis=show[n.lvl]&&(!t||n.type===t);n.el.style.display=show[n.lvl]?"":"none";
  n.el.classList.toggle("dim",!vis||(tr&&!tr.seen.has(n.k)));n.el.classList.toggle("sel",sel===n);n.el.classList.toggle("hl",!!(tr&&tr.seen.has(n.k)&&sel!==n))});
 D.edges.forEach(e=>{const vis=show[byK[e.s].lvl]&&show[byK[e.t].lvl];e.el.style.display=vis?"":"none";e.el.classList.toggle("hl",!!(tr&&tr.es.has(e)));e.el.classList.toggle("dim",!!(tr&&!tr.es.has(e)))})}
function esc(s){return String(s).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]))}
function val(v){return esc(Array.isArray(v)?v.join(", "):typeof v==="object"&&v!==null?JSON.stringify(v):v)}
function pick(n){sel=n;const rows=Object.entries(n.meta).concat(Object.entries(n.attrs));
 const links=D.edges.filter(e=>e.s===n.k||e.t===n.k).map(e=>{const o=byK[e.s===n.k?e.t:e.s];return `<li>${e.s===n.k?"→":"←"} ${esc(e.mid?e.mid+" ":"")}<b>${esc(e.rel)}</b> <a class="lnk" data-k="${esc(o.k)}">${esc(o.name)}</a> <span class="muted">${esc(o.type)}</span></li>`});
 document.getElementById("side").innerHTML=`<h2>${esc(n.name)}</h2><div class="muted">${esc(n.type)} · ${esc(n.id)}@${esc(n.v)}</div>
 <h3>Details</h3><table>${rows.map(([k,v])=>`<tr><td>${esc(k)}</td><td>${val(v)}</td></tr>`).join("")||"<tr><td colspan=2>none</td></tr>"}</table>
 <h3>Links (${links.length})</h3><ul>${links.join("")||"<li>none</li>"}</ul>`;
 document.querySelectorAll("a.lnk").forEach(a=>a.onclick=()=>{const o=byK[a.dataset.k];pick(o);o.el.scrollIntoView({block:"center",inline:"center",behavior:"smooth"})});paint()}
ts.onchange=paint;document.getElementById("dir").onchange=paint;document.getElementById("comp").onchange=paint;
document.getElementById("zin").onclick=()=>{zoom=Math.min(3,zoom*1.25);size()};document.getElementById("zout").onclick=()=>{zoom=Math.max(.3,zoom/1.25);size()};
document.getElementById("theme").onclick=()=>{const r=document.documentElement;const dark=r.dataset.theme?r.dataset.theme==="dark":matchMedia("(prefers-color-scheme: dark)").matches;r.dataset.theme=dark?"light":"dark"};
paint();
if(location.hash){const [id,dir]=decodeURIComponent(location.hash.slice(1)).split("/");const n=D.nodes.find(x=>x.id===id);if(n){if(dir)document.getElementById("dir").value=dir;pick(n)}}
</script></body></html>
'''
