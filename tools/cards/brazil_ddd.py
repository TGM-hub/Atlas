"""Fiche Brésil : indicatifs DDD, limites réelles.
Limites : communes IBGE (tbrugz/geodata-br) fusionnées par DDD selon kelvins/municipios-brasileiros ;
villes-repères et couleurs de zone reprises de l'appli DDD Brasil (TGM-hub/brasil-phone-code)."""
import os, sys, json
sys.path.insert(0, os.path.dirname(__file__))
from cardlib import *
from shapely.geometry import shape, mapping, Point
from shapely.ops import unary_union

B = os.path.join(D, "br")
AREAS = json.load(open(f"{B}/ddd_areas.geojson"))["features"]
APP = json.load(open(f"{B}/ddd_data.json"))
CITY = APP["DDD"]   # code : [ville, UF, lat, lon]
ZONE_COLOR = {1:"#C9A9E0",2:"#DCD39A",3:"#F0A860",4:"#5CC9C4",5:"#8FE0BC",6:"#EFE04A",7:"#F0A0DC",8:"#EE7A6A",9:"#57D06A"}
ZONE_NAME = {1:"São Paulo",2:"Rio de Janeiro et Espírito Santo",3:"Minas Gerais",4:"Paraná et Santa Catarina",5:"Rio Grande do Sul",
             6:"Centre-Ouest, Acre, Rondônia, Tocantins",7:"Bahia et Sergipe",8:"Nordeste (PE, AL, PB, RN, CE, PI)",9:"Nord et Maranhão"}
assert sorted(a["properties"]["ddd"] for a in AREAS) == sorted(CITY), "DDD manquants"

P = Proj(-74.2, -32.6, -34.0, 5.6, 3100)
from shapely.geometry import Polygon, MultiPolygon
def no_holes(g):   # lacs et grands fleuves : on bouche les trous intérieurs
    g = shape(g)
    parts = list(g.geoms) if g.geom_type == "MultiPolygon" else [g]
    return mapping(MultiPolygon([Polygon(p.exterior) for p in parts]))
fills, labels, dots, placed = [], [], [], []
free = lambda b: all(b[2] < o[0] or b[0] > o[2] or b[3] < o[1] or b[1] > o[3] for o in placed)
for c, (name, uf, lat, lon) in CITY.items():   # points des villes d'abord (réservés)
    x, y = P(lon, lat); placed.append((x - 7, y - 7, x + 7, y + 7))
    dots.append(f'<circle class="ct" cx="{x:.0f}" cy="{y:.0f}" r="5"/>')
for c, (name, uf, lat, lon) in CITY.items():   # noms de ville là où il reste de la place
    x, y = P(lon, lat); w = len(name) * 10.2
    for bx, tx, ty, anc in (((x + 8, y - 26, x + 10 + w, y - 4), x + 9, y - 8, "start"), ((x + 8, y + 2, x + 10 + w, y + 24), x + 9, y + 20, "start"),
                            ((x - 10 - w, y - 26, x - 8, y - 4), x - 9, y - 8, "end"), ((x - 10 - w, y + 2, x - 8, y + 24), x - 9, y + 20, "end")):
        if free(bx):
            placed.append(bx); labels.append(f'<text class="ctl" x="{tx:.0f}" y="{ty:.0f}" text-anchor="{anc}">{name}</text>'); break
for a in sorted(AREAS, key=lambda a: -shape(a["geometry"]).area):
    c = a["properties"]["ddd"]; a["geometry"] = no_holes(a["geometry"])
    fills.append(f'<path class="dd" fill="{ZONE_COLOR[int(c[0])]}" d="{path(a["geometry"], P, 0.6)}"/>')
    x, y, area = label_point(a["geometry"], P)
    fs0 = int(max(26, min(64, area ** 0.5 / 5.5)))
    geom = shape(a["geometry"]); done = False
    for fs in (fs0, int(fs0 * .8), 24):
        for dx, dy in ((0, 0), (0, -fs), (0, fs), (-fs, 0), (fs, 0), (0, -1.8 * fs), (0, 1.8 * fs), (-1.8 * fs, 0), (1.8 * fs, 0)):
            w = fs * 1.1; bx = (x + dx - w / 2, y + dy - fs * .5, x + dx + w / 2, y + dy + fs * .45)
            if free(bx) and geom.contains(Point(P.inv(x + dx, y + dy))): done = True; break
        if done: break
    if not done: fs, dx, dy = fs0, 0, 0
    placed.append(bx)
    labels.append(f'<text class="code" x="{x+dx:.0f}" y="{y + dy + fs*0.35:.0f}" style="font-size:{fs}px">{c}</text>')
states = "".join(f'<path class="uf" d="{path(f["geometry"], P, 0.6)}"/>' for f in admin1("BR"))
uflab = "".join(f'<text class="ufl" x="{P(*label_point_ll)[0]:.0f}" y="{P(*label_point_ll)[1]:.0f}">{f["properties"]["postal"]}</text>'
                for f in admin1("BR") for label_point_ll in [(lambda g: (g.representative_point().x, g.representative_point().y - 0.0))(shape(f["geometry"]))]) if False else ""
cn = lambda lon, lat, t: f'<text class="cn" x="{P(lon,lat)[0]:.0f}" y="{P(lon,lat)[1]:.0f}">{t}</text>'
svg = f'''<svg width="{P.w}" height="{P.h}" viewBox="0 0 {P.w} {P.h}">
<rect width="100%" height="100%" class="sea"/>{neighbours(P, {"BR"})}
{"".join(fills)}{states}
<image href="{relief(P, 180)}" width="{P.w}" height="{P.h}" class="relief"/>
{"".join(dots)}{"".join(labels)}
{cn(-66.5,-17,"Bolivie")}{cn(-58.5,-23.3,"Paraguay")}{cn(-64,-30,"Argentine")}{cn(-56,-33,"Uruguay")}{cn(-73,-9.8,"Pérou")}{cn(-72,1.5,"Colombie")}{cn(-65.5,6.0,"Venezuela")}{cn(-58.8,4.6,"Guyana")}{cn(-38,-25,"Atlantique")}
</svg>'''
legend = "".join(f'<div class="lg"><i style="background:{ZONE_COLOR[z]}"></i><b>{z}x</b> {n}</div>' for z, n in ZONE_NAME.items())
html = f'''<!doctype html><meta charset="utf-8"><style>{fonts()}{BASE_CSS}
#card{{width:{P.w + 100}px;padding:44px 50px 30px;display:flex;flex-direction:column;gap:22px}}
.map{{border-radius:8px;overflow:hidden}}
.dd{{stroke:#0e2130;stroke-width:1.2;stroke-linejoin:round}} .uf{{fill:none;stroke:#0e2130;stroke-width:3.4;stroke-linejoin:round}}
.code{{font-family:ui;font-weight:600;fill:#0e2130;text-anchor:middle;paint-order:stroke;stroke:#ffffffb0;stroke-width:6px}}
.ct{{fill:#fff;stroke:#0e2130;stroke-width:2.5}} .ctl{{font-family:ui;font-weight:600;font-size:19px;fill:#fff;paint-order:stroke;stroke:#0e2130;stroke-width:4px;stroke-linejoin:round}}
.legend{{display:grid;grid-template-columns:repeat(3,1fr);gap:10px 30px;font-size:27px}} .lg i{{display:inline-block;width:26px;height:26px;border-radius:4px;margin-right:10px;vertical-align:-4px}}
.lg b{{font-size:30px;margin-right:6px}} .note{{font-family:txt;font-size:22px;color:#8ea6b4}}
</style><div id="card"><h1>Indicatifs DDD<span>Brésil · limites réelles, ville principale de chaque DDD</span></h1>
<div class="map">{svg}</div><div class="legend">{legend}</div>
<div class="note">Le 1er chiffre donne la zone (couleur). Numéros : fixe (DDD) + 8 chiffres, mobile (DDD) + 9 chiffres. Points blancs = ville de référence de l'appli DDD Brasil. Traits épais = limites d'État.</div>
<div class="foot">Atlas TGM · limites : IBGE via geodata-br, DDD par commune : municipios-brasileiros · villes : appli DDD Brasil · fond : Natural Earth</div></div>'''
out = os.path.join(os.path.dirname(__file__), "brazil_ddd")
open(out + ".html", "w", encoding="utf-8").write(html)
render(out + ".html", out + ".png", width=P.w + 100)
print("ok", P.w, P.h)
