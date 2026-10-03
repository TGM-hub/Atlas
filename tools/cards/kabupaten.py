"""Fiches Indonésie : kabupaten et kota par grande île (geoBoundaries ADM2, CC BY 4.0 ; provinces Natural Earth).
Usage : python kabupaten.py java|sumatra|kalimantan|sulawesi|nusa"""
import os, sys, json
sys.path.insert(0, os.path.dirname(__file__))
from cardlib import *
from shapely.geometry import shape, Point
from shapely.ops import polylabel

REGIONS = {  # clé : (titre, lon0, lon1, lat0, lat1, largeur px)
 "java":       ("Java, Madura et Bali", 105.05, 115.75, -8.95, -5.75, 4200),
 "sumatra":    ("Sumatra",               95.0, 106.4, -6.0, 6.0, 2700),
 "kalimantan": ("Kalimantan",           108.6, 119.4, -4.3, 4.4, 3200),
 "sulawesi":   ("Sulawesi",             118.7, 125.4, -6.4, 2.0, 2700),
 "nusa":       ("Nusa Tenggara",        115.75, 125.2, -11.05, -7.75, 4200),
}
PROVS = {
 "java": {"Banten","Jakarta Raya","Jawa Barat","Jawa Tengah","Yogyakarta","Jawa Timur","Bali"},
 "sumatra": {"Aceh","Sumatera Utara","Sumatera Barat","Riau","Kepulauan Riau","Jambi","Bengkulu","Sumatera Selatan","Bangka-Belitung","Lampung"},
 "kalimantan": {"Kalimantan Barat","Kalimantan Tengah","Kalimantan Selatan","Kalimantan Timur","Kalimantan Utara"},
 "sulawesi": {"Sulawesi Utara","Gorontalo","Sulawesi Tengah","Sulawesi Barat","Sulawesi Selatan","Sulawesi Tenggara"},
 "nusa": {"Nusa Tenggara Barat","Nusa Tenggara Timur"},
}
SKIP = {"Hutan", "Wadung Kedungombo", "Waduk Cirata", "Waduk Kedungombo"}   # lacs/forêts, pas des entités administratives
RENAME = {"Kota Baru": "Kotabaru"}   # kabupaten (Kalimantan Sud), pas une kota
PROV_COL = ["#e8a54b","#4fb3d9","#7fc77a","#d77fbf","#e3c89a","#a58ee6","#3fbfa0","#e07a4f","#d9cf55","#8fb3c9","#c7a37a","#e35d6a"]

key = sys.argv[1] if len(sys.argv) > 1 else "java"
title, *box, W = REGIONS[key]
P = Proj(*box, W)
lon0, lon1, lat0, lat1 = box
D2 = json.load(open(f"{D}/idn_adm2.geojson"))
provs = [(f["properties"]["name"], shape(f["geometry"]), f) for f in admin1("ID")]

def prov_of(pt):
    for n, g, _ in provs:
        if g.contains(pt): return n
    return min(provs, key=lambda p: p[1].distance(pt))[0]

units = []
for f in D2["features"]:
    n = f["properties"]["shapeName"]
    if n in SKIP: continue
    n = RENAME.get(n, n)
    g = shape(f["geometry"])
    rp = g.representative_point()
    if not (lon0 <= rp.x <= lon1 and lat0 <= rp.y <= lat1): continue
    pv = prov_of(rp)
    if n in {"Bulungan", "Malinau", "Nunukan", "Tana Tidung", "Kota Tarakan"}: pv = "Kalimantan Utara"   # province créée en 2012, absente de Natural Earth
    if pv not in PROVS[key]: continue
    units.append({"name": n, "kota": n.startswith("Kota "), "geom": g, "f": f, "prov": pv})

prov_names = sorted({u["prov"] for u in units}, key=lambda p: min(u["geom"].centroid.x for u in units if u["prov"] == p))
pcol = {p: PROV_COL[i % len(PROV_COL)] for i, p in enumerate(prov_names)}

# --- étiquettes avec évitement des collisions (on préfère perdre une étiquette que d'en superposer)
placed, labels, dropped = [], [], []
def fits(bx):
    return all(bx[2] < b[0] or bx[0] > b[2] or bx[3] < b[1] or bx[1] > b[3] for b in placed) and \
           bx[0] > 0 and bx[1] > 0 and bx[2] < P.w and bx[3] < P.h
def lp(g):
    parts = list(g.geoms) if g.geom_type == "MultiPolygon" else [g]
    big = max(parts, key=lambda p: p.area)
    from shapely.geometry import Polygon
    pp = Polygon([P(x, y) for x, y in big.exterior.coords]).buffer(0)
    pt = polylabel(pp, tolerance=0.5)
    return pt.x, pt.y, pp.area
kab = sorted([u for u in units if not u["kota"]], key=lambda u: -u["geom"].area)
kota = sorted([u for u in units if u["kota"]], key=lambda u: -u["geom"].area)
jakarta_done = False
for u in kota:
    nm = u["name"][5:]
    if nm.startswith("Jakarta"):
        if jakarta_done: continue
        nm, jakarta_done = "Jakarta", True
    x, y, a = lp(u["geom"])
    fs = 17; w = len(nm) * fs * 0.47
    for dx, anchor in ((9, "start"), (-9, "end")):
        bx = (x + dx, y - 9, x + dx + w, y + 6) if anchor == "start" else (x + dx - w, y - 9, x + dx, y + 6)
        if fits(bx):
            placed.append(bx); placed.append((x - 5, y - 5, x + 5, y + 5))
            labels.append(f'<circle class="kd" cx="{x:.0f}" cy="{y:.0f}" r="5"/><text class="kt" x="{x+dx:.0f}" y="{y+5:.0f}" text-anchor="{anchor}">{nm}</text>'); break
    else:
        labels.append(f'<circle class="kd" cx="{x:.0f}" cy="{y:.0f}" r="4"/>'); dropped.append(u["name"])

for u in kab:
    x, y, a = lp(u["geom"])
    done = False
    top = int(max(18, min(34, a ** 0.5 / 7)))
    for fs in sorted({top, int(top * .85), 18, 16, 14}, reverse=True):
        w = len(u["name"]) * fs * 0.47
        for dy in (0, -fs, fs, -2 * fs, 2 * fs):
            yy = y + dy
            bx = (x - w / 2 - 3, yy - fs * .75, x + w / 2 + 3, yy + fs * .3)
            if fits(bx) and u["geom"].buffer(0.02).contains(Point(P.inv(x, yy - fs * .25))):
                placed.append(bx); labels.append(f'<text class="kb" x="{x:.0f}" y="{yy:.0f}" style="font-size:{fs}px">{u["name"]}</text>'); done = True; break
        if done: break
    if not done: dropped.append(u["name"])
polys = "".join(f'<path class="{"ko" if u["kota"] else "ka"}" fill="{"#f1ece0" if u["kota"] else pcol[u["prov"]]}" d="{path(u["f"]["geometry"], P, 0.4)}"/>' for u in units)
from shapely.ops import unary_union
from shapely.geometry import mapping
pborders = "".join(f'<path class="pv" d="{path(mapping(unary_union([u["geom"].buffer(0.003) for u in units if u["prov"] == p]).buffer(-0.003)), P, 0.4)}"/>' for p in prov_names)
svg = f'''<svg width="{P.w}" height="{P.h}" viewBox="0 0 {P.w} {P.h}">
<rect width="100%" height="100%" class="sea"/>{neighbours(P, {"ID"})}
{polys}{pborders}
<image href="{relief(P, 150)}" width="{P.w}" height="{P.h}" class="relief"/>
{"".join(labels)}</svg>'''
legend = "".join(f'<span class="lg"><i style="background:{pcol[p]}"></i>{p} <small>{sum(1 for u in units if u["prov"]==p and not u["kota"])} kab. · {sum(1 for u in units if u["prov"]==p and u["kota"])} kota</small></span>' for p in prov_names)
html = f'''<!doctype html><meta charset="utf-8"><style>{fonts()}{BASE_CSS}
#card{{width:{P.w + 100}px;padding:44px 50px 30px;display:flex;flex-direction:column;gap:20px}}
.map{{border-radius:8px;overflow:hidden}}
.ka{{stroke:#0e2130;stroke-width:.9;stroke-linejoin:round;fill-opacity:.92}} .ko{{stroke:#0e2130;stroke-width:.9}}
.pv{{fill:none;stroke:#0e2130;stroke-width:3.2;stroke-linejoin:round}}
.kb{{font-family:ui;font-weight:600;fill:#0e2130;text-anchor:middle;paint-order:stroke;stroke:#ffffff90;stroke-width:3.5px}}
.kd{{fill:#0e2130;stroke:#fff;stroke-width:2}}
.kt{{font-family:ui;font-weight:600;font-size:17px;font-style:italic;fill:#fff;paint-order:stroke;stroke:#0e2130;stroke-width:3.5px}}
.legend{{display:flex;flex-wrap:wrap;gap:10px 30px;font-size:27px}} .lg i{{display:inline-block;width:24px;height:24px;border-radius:4px;margin-right:8px;vertical-align:-3px}}
.lg small{{color:#8ea6b4;font-size:21px}} .key{{font-family:txt;font-size:21px;color:#c8d6de}}
</style><div id="card"><h1>Kabupaten et kota<span>Indonésie · {title}</span></h1>
<div class="map">{svg}</div><div class="legend">{legend}</div>
<div class="key">Texte foncé = kabupaten (régence) · <b style="color:#fff">zone claire + ● nom en italique</b> = kota (ville autonome) {'· Jakarta = 5 kota regroupées ' if key == 'java' else ''}· traits épais = limites de province{f" · {len(dropped)} noms masqués faute de place" if dropped else ""}</div>
<div class="foot">Atlas TGM · limites : geoBoundaries (CC BY 4.0) et Natural Earth · fond : Natural Earth</div></div>'''
out = os.path.join(os.path.dirname(__file__), f"kab_{key}")
open(out + ".html", "w", encoding="utf-8").write(html)
render(out + ".html", out + ".png", width=P.w + 100)
print(key, len(units), "unités,", len(dropped), "masqués :", dropped)
