"""Fiches Indonésie : (1) les 38 provinces, (2) les zones de plaques d'immatriculation.
Sources : data/id_admin.json, extrait du trainer indonesia-kabupaten (TGM-hub) :
  contours geoBoundaries ADM2 (BPS / OCHA, CC BY 3.0 IGO), codes et chefs-lieux Kepmendagri 2025 (cahyadsn/wilayah, MIT),
  préfixes de plaques Wikipedia (« Vehicle registration plates of Indonesia »). Fond : Natural Earth."""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from cardlib import *
from shapely.geometry import shape, Polygon, LineString, mapping
from shapely.ops import unary_union, polylabel

HERE = os.path.dirname(__file__)
D_ = json.load(open(os.path.join(HERE, "data", "id_admin.json"), encoding="utf-8"))
PROVS, UNITS = D_["provinces"], D_["units"]
CAPITAL_FIX = {"62": "Palangka Raya", "94": "Nabire", "95": "Wamena"}  # coquilles / nom de kabupaten dans la source
for c, n in CAPITAL_FIX.items():
    PROVS[c]["capital"] = n
assert len(PROVS) == 38 and len(UNITS) == 514
ISL = [("Sumatra", "Sumatra", "#e3a64f"), ("Java", "Java", "#e06a5a"), ("Bali & Nusa Tenggara", "Bali et Nusa Tenggara", "#d98ccf"),
       ("Kalimantan", "Kalimantan", "#5fbf7a"), ("Sulawesi", "Sulawesi", "#58b7d6"), ("Maluku", "Moluques", "#c8b45a"),
       ("Papua", "Papouasie", "#a993e0")]
ICOL = {k: c for k, _, c in ISL}


def mp(polys):
    return {"type": "MultiPolygon", "coordinates": polys}


def shade(hexc, f):
    r, g, b = (int(hexc[i:i + 2], 16) for i in (1, 3, 5))
    t = (lambda v: round(v + (255 - v) * f)) if f > 0 else (lambda v: round(v * (1 + f)))
    return "#%02x%02x%02x" % (t(r), t(g), t(b))


def colouring(geoms, n):
    """Coloriage glouton : deux zones voisines n'ont pas la même teinte (n teintes)."""
    keys = sorted(geoms, key=lambda k: -geoms[k].area)
    col = {}
    for k in keys:
        used = {col[j] for j in col if geoms[k].buffer(0.02).intersects(geoms[j])}
        col[k] = next(i for i in range(n) if i not in used)
    return col


def label_at(g, P, text_w, fs):
    """Point d'étiquette dans le plus grand morceau, et si le texte y tient."""
    parts = list(g.geoms) if g.geom_type == "MultiPolygon" else [g]
    big = max((Polygon([P(*xy) for xy in p.exterior.coords]).buffer(0) for p in parts), key=lambda p: p.area)
    pt = polylabel(big, tolerance=0.5)
    line = LineString([(pt.x - text_w / 2, pt.y), (pt.x + text_w / 2, pt.y)])
    return pt.x, pt.y, big.contains(line) and big.exterior.distance(pt) > fs * 0.5


FONTS_CSS = fonts()
CSS = f"""{FONTS_CSS}{BASE_CSS}
#card{{width:2700px;padding:44px 50px 30px;display:flex;flex-direction:column;gap:22px}}
.map{{border-radius:8px;overflow:hidden}}
.st{{stroke:#0e2130;stroke-width:1;stroke-linejoin:round}} .kb{{fill:none;stroke:#0e213055;stroke-width:.6}}
.pn{{font-family:ui;font-weight:600;fill:#0e2130;text-anchor:middle;paint-order:stroke;stroke:#ffffff99;stroke-width:4px}}
.nb circle{{fill:#0e2130;stroke:#fff;stroke-width:2}} .nb text{{font-family:ui;font-weight:600;fill:#fff;text-anchor:middle}}
.pl rect{{fill:#111;stroke:#f5f5f5;stroke-width:2.5}} .pl text{{font-family:ui;font-weight:600;fill:#f5f5f5;text-anchor:middle;letter-spacing:.04em}}
.frame{{fill:none;stroke:#f2c94c;stroke-width:3;stroke-dasharray:10 6}} .fl{{font-family:ui;font-size:22px;fill:#f2c94c}}
h3{{margin:0 0 12px;font-size:30px;color:#f2c94c;font-weight:600}}
.note{{font-family:txt;font-size:20px;color:#8ea6b4;line-height:1.4}}
"""
cn = lambda P, lon, lat, t, cls="cn": f'<text class="{cls}" x="{P(lon,lat)[0]:.0f}" y="{P(lon,lat)[1]:.0f}">{t}</text>'
NEIGH_LABELS = lambda P: (cn(P, 102.4, 4.6, "Malaisie") + cn(P, 115.2, 4.3, "Malaisie") + cn(P, 122.6, 7.6, "Philippines")
                          + cn(P, 126.1, -8.2, "Timor-Leste"))
P = Proj(94.8, 141.3, -11.3, 6.6, 2600)

# ---------------------------------------------------------------- 1. provinces
pg = {c: shape(mp(p["poly"])) for c, p in PROVS.items()}
tone = {}
for isl, _, _ in ISL:
    sub = {c: pg[c] for c in PROVS if PROVS[c]["island"] == isl}
    tone.update(colouring(sub, 4))
TONES = [0, .28, -.18, .5]
order = [c for isl, _, _ in ISL for c in sorted(PROVS) if PROVS[c]["island"] == isl]
NUM = {c: i + 1 for i, c in enumerate(order)}
fills, labels = [], []
for c in order:
    fills.append(f'<path class="st" fill="{shade(ICOL[PROVS[c]["island"]], TONES[tone[c]])}" d="{path(mp(PROVS[c]["poly"]), P, 0.4)}"/>')
    fs, n = 21, PROVS[c]["name"]
    x, y, fits = label_at(pg[c], P, len(n) * fs * 0.42 + 4, fs)
    if fits:
        labels.append(f'<text class="pn" x="{x:.0f}" y="{y + fs * .34:.0f}" style="font-size:{fs}px">{n}</text>')
    else:
        labels.append(f'<g class="nb"><circle cx="{x:.0f}" cy="{y:.0f}" r="15"/><text x="{x:.0f}" y="{y + 6:.0f}" style="font-size:19px">{NUM[c]}</text></g>')
svg = f'''<svg width="{P.w}" height="{P.h}" viewBox="0 0 {P.w} {P.h}">
<rect width="100%" height="100%" class="sea"/>{neighbours(P, {"ID"})}{"".join(fills)}
<image href="{relief(P, 230)}" width="{P.w}" height="{P.h}" class="relief"/>{"".join(labels)}{NEIGH_LABELS(P)}</svg>'''
cols = ""
for isl, fr, col in ISL:
    cs = [c for c in order if PROVS[c]["island"] == isl]
    rows = "".join(f'<li><b>{NUM[c]}</b>{PROVS[c]["name"]}<em>{PROVS[c]["capital"]}</em></li>' for c in cs)
    cols += f'<div class="rg"><h4><i style="background:{col}"></i>{fr}<small>{len(cs)}</small></h4><ul>{rows}</ul></div>'
html = f'''<!doctype html><meta charset="utf-8"><style>{CSS}
.lists{{columns:4;column-gap:40px}} .rg{{break-inside:avoid;margin-bottom:20px}}
.rg h4{{margin:0 0 6px;font-size:28px;font-weight:600;display:flex;align-items:center;gap:10px}}
.rg h4 i{{width:24px;height:24px;border-radius:4px}} .rg h4 small{{color:#8ea6b4;font-weight:400;font-size:22px}}
.rg ul{{list-style:none;margin:0;padding:0;font-family:txt;font-size:22px;color:#c8d6de}} .rg li{{line-height:1.5}}
.rg li b{{display:inline-block;width:38px;font-family:ui;color:#f2c94c}} .rg li em{{font-style:normal;color:#8ea6b4;margin-left:10px;font-size:19px}}
</style><div id="card"><h1>Provinces<span>Indonésie · les 38 provinces (depuis la partition de la Papouasie, 2022)</span></h1>
<div class="map">{svg}</div>
<div class="lists">{cols}</div>
<div class="note">En gris clair après chaque nom : le chef-lieu. Teintes = grandes îles ; les nuances distinguent les provinces voisines. Les 6 provinces de Papouasie datent de 2022 : l'imagerie plus ancienne et certaines enseignes indiquent encore « Papua » ou « Papua Barat ».</div>
<div class="foot">Atlas TGM · contours : geoBoundaries (BPS, OCHA, CC BY 3.0 IGO) · provinces et chefs-lieux : Kepmendagri 2025 (cahyadsn/wilayah) · fond : Natural Earth</div></div>'''
open(os.path.join(HERE, "indonesia_provinces.html"), "w", encoding="utf-8").write(html)
render(os.path.join(HERE, "indonesia_provinces.html"), os.path.join(HERE, "indonesia_provinces.png"))
print("provinces ok", P.w, P.h)

# ---------------------------------------------------------------- 2. plaques
zones = {}
for u in UNITS:
    zones.setdefault(u["plate"], []).append(u)
zg = {k: unary_union([shape(mp(u["poly"])).buffer(0) for u in us]) for k, us in zones.items()}
zcol = colouring(zg, 6)
PAL = ["#e3a64f", "#58b7d6", "#e06a5a", "#5fbf7a", "#a993e0", "#d9cf55"]
assert sum(len(v) for v in zones.values()) == 514


def describe(code):
    us = zones[code]
    provs = sorted({u["province_code"] for u in us})
    whole = [p for p in provs if all(u["plate"] == code for u in UNITS if u["province_code"] == p)]
    if len(whole) == len(provs):
        return ", ".join(PROVS[p]["name"] for p in provs)
    names = []
    for u in us:
        base = u["name"]
        if base not in names:
            names.append(base)
    return ", ".join(names)


ORDER_PL = [k for isl, _, _ in ISL for k in sorted(zones, key=lambda z: (min(u["code"] for u in zones[z])))
            if PROVS[min(u["code"] for u in zones[k])[:2]]["island"] == isl]
JX0, JX1, JY0, JY1 = 105.05, 117.1, -9.0, -5.75


def plate_map(P, skip_box=None, fs=22, kab_lines=False):
    fills, labs = [], []
    for k in ORDER_PL:
        fills.append(f'<path class="st" fill="{PAL[zcol[k]]}" d="{path(mapping(zg[k]), P, 0.4)}"/>')
    if kab_lines:
        fills.extend(f'<path class="kb" d="{path(mp(u["poly"]), P, 0.6)}"/>' for u in UNITS
                     if JX0 - 1 < shape(mp(u["poly"])).centroid.x < JX1 + 1 and shape(mp(u["poly"])).centroid.y > JY0 - 1)
    for k in ORDER_PL:
        g = zg[k]
        if skip_box:
            c = g.representative_point()
            if skip_box[0] < c.x < skip_box[1] and skip_box[2] < c.y < skip_box[3]:
                continue
        w = len(k) * fs * .62 + 16
        x, y, fits = label_at(g, P, w, fs)
        if not (0 < x < P.w and 0 < y < P.h):
            continue
        labs.append(f'<g class="pl"><rect x="{x - w/2:.0f}" y="{y - fs*.75:.0f}" width="{w:.0f}" height="{fs*1.5:.0f}" rx="4"/>'
                    f'<text x="{x:.0f}" y="{y + fs*.36:.0f}" style="font-size:{fs}px">{k}</text></g>')
    return fills, labs


f1, l1 = plate_map(P, skip_box=(JX0, JX1, JY0, JY1), fs=22)
x0, y0 = P(JX0, JY1); x1, y1 = P(JX1, JY0)
svg1 = f'''<svg width="{P.w}" height="{P.h}" viewBox="0 0 {P.w} {P.h}">
<rect width="100%" height="100%" class="sea"/>{neighbours(P, {"ID"})}{"".join(f1)}
<image href="{relief(P, 230)}" width="{P.w}" height="{P.h}" class="relief"/>
<rect x="{x0:.0f}" y="{y0:.0f}" width="{x1-x0:.0f}" height="{y1-y0:.0f}" class="frame"/><text class="fl" x="{x0+6:.0f}" y="{y0-10:.0f}">encart Java, Bali, Lombok</text>
{"".join(l1)}{NEIGH_LABELS(P)}</svg>'''
Q = Proj(JX0, JX1, JY0, JY1, 2600)
f2, l2 = plate_map(Q, fs=26, kab_lines=True)
svg2 = f'''<svg width="{Q.w}" height="{Q.h}" viewBox="0 0 {Q.w} {Q.h}">
<rect width="100%" height="100%" class="sea"/>{neighbours(Q, {"ID"})}{"".join(f2)}
<image href="{relief(Q, 200)}" width="{Q.w}" height="{Q.h}" class="relief"/>{"".join(l2)}
{cn(Q,106.8,-5.95,"Mer de Java")}{cn(Q,110.5,-8.75,"Océan Indien")}</svg>'''
legend = ""
for isl, fr, _ in ISL:
    ks = [k for k in ORDER_PL if PROVS[min(u["code"] for u in zones[k])[:2]]["island"] == isl]
    rows = "".join(f'<li><span class="pk">{k}</span>{describe(k)}</li>' for k in ks)
    legend += f'<div class="rg"><h4>{fr}</h4><ul>{rows}</ul></div>'
html = f'''<!doctype html><meta charset="utf-8"><style>{CSS}
.lists{{columns:3;column-gap:44px}} .rg{{break-inside:avoid;margin-bottom:18px}}
.rg h4{{margin:0 0 6px;font-size:28px;font-weight:600;color:#f2c94c}}
.rg ul{{list-style:none;margin:0;padding:0;font-family:txt;font-size:20px;color:#c8d6de}} .rg li{{line-height:1.35;margin-bottom:6px;display:flex;gap:12px}}
.pk{{flex:0 0 auto;min-width:52px;text-align:center;background:#111;color:#f5f5f5;border:2px solid #f5f5f5;border-radius:4px;font-family:ui;font-weight:600;font-size:22px;padding:0 6px;height:30px;line-height:26px}}
</style><div id="card"><h1>Plaques<span>Indonésie · préfixe régional des plaques d'immatriculation</span></h1>
<div class="map">{svg1}</div><div class="map">{svg2}</div>
<div class="lists">{legend}</div>
<div class="note">Le préfixe (1 à 2 lettres, avant le numéro) désigne le lieu d'immatriculation, pas la position du véhicule : à croiser avec d'autres indices. Couleurs sans signification, seulement pour séparer les zones voisines. Papouasie : préfixes PG, PS, PT, PY introduits après la partition de 2022 ; l'imagerie plus ancienne montre PA ou PB.</div>
<div class="foot">Atlas TGM · préfixes : Wikipedia (Vehicle registration plates of Indonesia) · contours : geoBoundaries (BPS, OCHA, CC BY 3.0 IGO) · fond : Natural Earth</div></div>'''
open(os.path.join(HERE, "indonesia_plates.html"), "w", encoding="utf-8").write(html)
render(os.path.join(HERE, "indonesia_plates.html"), os.path.join(HERE, "indonesia_plates.png"))
print("plates ok", Q.w, Q.h, len(zones), "zones")
