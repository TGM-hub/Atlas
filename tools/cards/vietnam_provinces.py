"""Fiche Vietnam : les 63 provinces (découpage d'avant juillet 2025) par grande région.
Sources : géométries et régions du trainer vietnam-province-guesser (data/vn_provinces.json, extrait de son index.html) ;
noms et unités fusionnées en 2025 recoupés avec Wikipedia (« Provinces of Vietnam », résolution 202/2025/QH15).
Le fond (pays voisins, relief) vient de Natural Earth."""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from cardlib import *
from shapely.geometry import Polygon, MultiPolygon, LineString
from shapely.ops import polylabel

HERE = os.path.dirname(__file__)
PROV = json.load(open(os.path.join(HERE, "data", "vn_provinces.json"), encoding="utf-8"))
REGIONS = [  # (clé du trainer, libellé, couleur)
 ("Tây Bắc Bộ", "Tây Bắc", "#b79ad8"), ("Đông Bắc Bộ", "Đông Bắc", "#5cc46d"),
 ("Đồng bằng sông Hồng", "Đồng bằng sông Hồng", "#4fbfba"), ("Bắc Trung Bộ", "Bắc Trung Bộ", "#e3d24a"),
 ("Duyên hải Nam Trung Bộ", "Duyên hải Nam Trung Bộ", "#eba05a"), ("Tây Nguyên", "Tây Nguyên", "#88d6b2"),
 ("Đông Nam Bộ", "Đông Nam Bộ", "#e8786a"), ("Đồng bằng sông Cửu Long", "Đồng bằng sông Cửu Long", "#e59ad3")]
COL = {k: c for k, _, c in REGIONS}
assert len(PROV) == 63 and {p["reg"] for p in PROV.values()} == set(COL), "63 provinces / 8 régions attendues"

order = [k for r, _, _ in REGIONS for k in sorted((k for k in PROV if PROV[k]["reg"] == r), key=lambda k: PROV[k]["n"])]
NUM = {k: i + 1 for i, k in enumerate(order)}


def geom(k):
    return {"type": "MultiPolygon", "coordinates": [[r] for r in PROV[k]["r"]]}


def place(k, P, fs, simp=0.4):
    """Point d'étiquette ; renvoie (x, y, tient) : tient = le nom entre dans le polygone à cette taille."""
    parts = [Polygon([P(*pt) for pt in r]).buffer(0) for r in PROV[k]["r"] if len(r) > 3]
    big = max(parts, key=lambda p: p.area)
    pt = polylabel(big, tolerance=0.5)
    w = len(PROV[k]["n"]) * fs * 0.42 + 4
    line = LineString([(pt.x - w / 2, pt.y), (pt.x + w / 2, pt.y)])
    room = big.exterior.distance(pt) if big.contains(pt) else 0
    return pt.x, pt.y, big.contains(line) and room > fs * 0.5


def draw(P, fs, names_only=False, num_r=15):
    fills, labels = [], []
    for k in PROV:
        fills.append(f'<path class="st" fill="{COL[PROV[k]["reg"]]}" d="{path(geom(k), P, 0.4)}"/>')
    for k in PROV:
        x, y, fits = place(k, P, fs)
        if not (0 < x < P.w and 0 < y < P.h):
            continue
        if fits:
            labels.append(f'<text class="pn" x="{x:.0f}" y="{y + fs * 0.34:.0f}" style="font-size:{fs}px">{PROV[k]["n"]}</text>')
        elif not names_only:
            labels.append(f'<g class="nb"><circle cx="{x:.0f}" cy="{y:.0f}" r="{num_r}"/>'
                          f'<text x="{x:.0f}" y="{y + num_r * 0.42:.0f}" style="font-size:{num_r * 1.3:.0f}px">{NUM[k]}</text></g>')
    return fills, labels


P = Proj(101.9, 110.2, 8.35, 23.5, 1320)
fills, labels = draw(P, 22)
cn = lambda lon, lat, t: f'<text class="cn" x="{P(lon,lat)[0]:.0f}" y="{P(lon,lat)[1]:.0f}">{t}</text>'
# cadre de l'encart sur la carte principale
DX0, DX1, DY0, DY1 = 105.25, 107.05, 19.95, 21.45
x0, y0 = P(DX0, DY1); x1, y1 = P(DX1, DY0)
svg = f'''<svg width="{P.w}" height="{P.h}" viewBox="0 0 {P.w} {P.h}">
<rect width="100%" height="100%" class="sea"/>{neighbours(P, {"VN"})}
{"".join(fills)}
<image href="{relief(P, 230)}" width="{P.w}" height="{P.h}" class="relief"/>
<rect x="{x0:.0f}" y="{y0:.0f}" width="{x1-x0:.0f}" height="{y1-y0:.0f}" class="frame"/>
<text class="fl" x="{x1 + 8:.0f}" y="{y0 + 4:.0f}">encart</text>
{"".join(labels)}
{cn(104.2,23.15,"Chine")}{cn(106.7,23.2,"Chine")}{cn(103.4,19.6,"Laos")}{cn(105.6,16.4,"Laos")}{cn(104.6,12.9,"Cambodge")}
{cn(108.6,17.6,"Mer de Chine")}{cn(103.7,10.6,"Golfe de Thaïlande")}
</svg>'''

Q = Proj(DX0, DX1, DY0, DY1, 1180)
qf, ql = draw(Q, 26, names_only=True)
inset = f'''<svg width="{Q.w}" height="{Q.h}" viewBox="0 0 {Q.w} {Q.h}">
<rect width="100%" height="100%" class="sea"/>{neighbours(Q, {"VN"})}{"".join(qf)}
<image href="{relief(Q, 200)}" width="{Q.w}" height="{Q.h}" class="relief"/>{"".join(ql)}</svg>'''

lists = ""
for r, lab, c in REGIONS:
    ks = [k for k in order if PROV[k]["reg"] == r]
    rows = "".join(f'<li><b>{NUM[k]}</b>{PROV[k]["n"]}{"" if PROV[k]["new"] == PROV[k]["n"] else f"<em>→ {PROV[k]['new']}</em>"}</li>' for k in ks)
    lists += f'<div class="rg"><h4><i style="background:{c}"></i>{lab}<small>{len(ks)}</small></h4><ul>{rows}</ul></div>'

html = f'''<!doctype html><meta charset="utf-8"><style>{fonts({"ui": FONT_FILES["ui"] + [("barlow-condensed-vietnamese", 400), ("barlow-condensed-vietnamese", 600)], "txt": FONT_FILES["txt"] + [("barlow-vietnamese", 400), ("barlow-vietnamese", 600)]})}{BASE_CSS}
#card{{width:2700px;padding:44px 50px 30px;display:flex;flex-direction:column;gap:22px}}
.map{{border-radius:8px;overflow:hidden}}
.st{{stroke:#0e2130;stroke-width:1.1;stroke-linejoin:round}}
.pn{{font-family:ui;font-weight:600;fill:#0e2130;text-anchor:middle;paint-order:stroke;stroke:#ffffff99;stroke-width:4px}}
.nb circle{{fill:#0e2130;stroke:#fff;stroke-width:2}} .nb text{{font-family:ui;font-weight:600;fill:#fff;text-anchor:middle}}
.frame{{fill:none;stroke:#f2c94c;stroke-width:3;stroke-dasharray:10 6}} .fl{{font-family:ui;font-size:22px;fill:#f2c94c}}
.row{{display:grid;grid-template-columns:{P.w}px 1fr;gap:40px}}
h3{{margin:0 0 12px;font-size:30px;color:#f2c94c;font-weight:600}}
.lists{{columns:2;column-gap:36px;margin-top:26px}}
.rg{{break-inside:avoid;margin-bottom:18px}}
.rg h4{{margin:0 0 6px;font-size:27px;font-weight:600;display:flex;align-items:center;gap:10px}}
.rg h4 i{{width:24px;height:24px;border-radius:4px}} .rg h4 small{{color:#8ea6b4;font-weight:400;font-size:22px}}
.rg ul{{list-style:none;margin:0;padding:0;font-family:txt;font-size:21px;color:#c8d6de}}
.rg li{{line-height:1.5}} .rg li b{{display:inline-block;width:36px;font-family:ui;color:#f2c94c;font-size:22px}}
.rg li em{{font-style:normal;color:#8ea6b4;margin-left:8px;font-size:18px}}
.note{{font-family:txt;font-size:20px;color:#8ea6b4;line-height:1.4;margin-top:6px}}
</style><div id="card"><h1>Provinces<span>Vietnam · les 63 provinces d'avant 2025, par grande région</span></h1>
<div class="row"><div class="map">{svg}</div>
<div><h3>Encart : delta du fleuve Rouge</h3><div class="map">{inset}</div>
<div class="note">Les enseignes et adresses en jeu suivent ce découpage. Depuis juillet 2025, les 63 provinces sont fusionnées en 34 : l'unité actuelle est indiquée après la flèche.</div>
<div class="lists">{lists}</div></div></div>
<div class="foot">Atlas TGM · provinces et régions : trainer « Tỉnh Việt Nam » (TGM-hub), Wikipedia · fusion de 2025 : résolution 202/2025/QH15 · fond : Natural Earth</div></div>'''
out = os.path.join(HERE, "vietnam_provinces")
open(out + ".html", "w", encoding="utf-8").write(html)
render(out + ".html", out + ".png")
print("ok", P.w, P.h, Q.w, Q.h)
