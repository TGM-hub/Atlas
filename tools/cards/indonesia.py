"""Fiche Indonésie : toits par région.
Sources : Plonk It Indonésie (citations relevées le 2026-10-03, voir commentaires), styles vernaculaires
recoupés avec les noms d'ethnies/régions établis (Minangkabau, Batak, Toraja, Sumba, Nias, Bali).
Les sommets de poteaux ne sont PAS repris : Plonk It en a déjà une carte."""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from cardlib import *

# Couche de fond : matériau dominant (Plonk It : « Tiled roofs are most commonly found on the island of Java, and sometimes
# nearby regions such as southern Sumatra, the Lesser Sunda Islands, and South Kalimantan » / « Plain sheet metal roofs
# are more commonly found toward the north … Kalimantan, Sulawesi and Sumatra » / tuiles différentes en Kalimantan Sud et Jambi)
BASE = {
 "tile":  ("Tuiles dominantes", "#d9733f", ["ID-BT","ID-JK","ID-JB","ID-JT","ID-YO","ID-JI"]),
 "mixed": ("Tuiles parfois, avec de la tôle", "#e9b07a", ["ID-LA","ID-SS","ID-JA","ID-BA","ID-NB","ID-NT","ID-KS"]),
 "metal": ("Tôle, tuiles quasi absentes", "#9fb3c2", ["ID-AC","ID-SU","ID-SB","ID-RI","ID-KR","ID-BE","ID-BB",
            "ID-KB","ID-KT","ID-KI","ID-SA","ID-GO","ID-ST","ID-SR","ID-SN","ID-SG"]),
}
NOINFO = ["ID-MA","ID-MU","ID-PA","ID-PB"]
FLAT_TILES = ["ID-KS", "ID-JA"]   # « The tiles on roofs in South Kalimantan and Jambi look slightly different. »

# Styles locaux : (n°, titre, zone, texte, positions des pastilles (lon, lat), pictogramme)
STYLES = [
 (1, "Pinacles en couronne", "Bali, partout", "Faîtes ornés de pinacles ; murs en andésite sombre fréquents", [(115.2, -8.35)], "bali"),
 (2, "Toit en bateau à flèches", "Sumatra Ouest", "Extrémités très relevées en pointes", [(100.45, -0.75)], "minang"),
 (3, "Toit en bateau sans flèches", "Sumatra Nord", "Moins relevé ; autour du lac Toba", [(98.9, 2.45)], "batak"),
 (4, "Feuilles de palmier, très pentu", "Nias", "Toits raides en palmes, rare", [(97.6, 1.1)], "nias"),
 (5, "Fentes horizontales dans le pignon", "Sulawesi Sud", "Presque unique à la région", [(119.75, -4.7)], "slot"),
 (6, "Tongkonan (toit en selle)", "Autour de Rantepao", "Petite zone de Sulawesi Sud", [(119.9, -2.95)], "tongkonan"),
 (7, "Sommets très pointus", "Sumba", "Toits à pic central très haut", [(119.95, -9.65)], "sumba"),
 (8, "Bardeaux de bois", "Kalimantan", "Toits en copeaux de bois", [(113.6, 0.6)], "wood"),
 (9, "Cornes de pignon", "Sulawesi Sud, Riau, Kalimantan centre et sud", "Pièces croisées dépassant au faîte",
     [(120.35, -3.75), (101.9, 0.25), (113.35, -1.75), (115.55, -2.6)], "horns"),
]

def picto(kind, w=110, h=70):
    """Schémas simplifiés (silhouettes), pas des dessins d'après photo."""
    s = 'stroke="#e6eef2" stroke-width="3" fill="none" stroke-linejoin="round" stroke-linecap="round"'
    body = {
     "bali": f'<path {s} d="M15 60h80M25 60V42h60v18M20 42l35-22 35 22"/><path {s} d="M55 20v-8M51 12h8M55 12l-3-5h6z"/>',
     "minang": f'<path {s} d="M20 62h70M28 62V44h54v18M12 14q20 34 43 22q23 12 43-22"/><path {s} d="M12 14l-4-8M98 14l4-8"/>',
     "batak": f'<path {s} d="M20 62h70M28 62V46h54v16M16 26q14 22 39 14q25 8 39-14"/>',
     "nias": f'<path {s} d="M30 62h50M36 62V50h38v12M24 50L55 8l31 42"/>',
     "slot": f'<path {s} d="M18 62h74M26 62V40h58v22M18 40l37-26 37 26"/><path {s} d="M44 30h22M40 35h30"/>',
     "tongkonan": f'<path {s} d="M30 62h50M38 62V46h34v16M6 18q49 40 98 0"/>',
     "sumba": f'<path {s} d="M14 62h82M22 62V46h66v16M14 46l28-8 13-32 13 32 28 8"/>',
     "wood": f'<path {s} d="M18 62h74M26 62V42h58v20M18 42l37-26 37 26"/><path stroke="#e6eef2" stroke-width="2" d="M33 36h10M48 30h10M63 36h10M40 24h8M58 24h8"/>',
     "horns": f'<path {s} d="M18 62h74M26 62V42h58v20M18 42l37-26 37 26M55 16l-8-10M55 16l8-10"/>',
    }[kind]
    return f'<svg width="{w}" height="{h}" viewBox="0 0 110 70">{body}</svg>'

feats = {f["properties"]["iso_3166_2"]: f for f in admin1("ID")}
klass = {c: k for k, (_, _, cs) in BASE.items() for c in cs}
assert set(klass) | set(NOINFO) == set(feats), set(feats) - set(klass) - set(NOINFO)

P = Proj(94.6, 127.4, -11.3, 6.3, 2600)
paths = []
for c, f in feats.items():
    if c in NOINFO: fill = "url(#noinfo)"
    else: fill = BASE[klass[c]][1]
    paths.append(f'<path class="st" fill="{fill}" d="{path(f["geometry"], P, 0.4)}"/>')
    if c in FLAT_TILES:
        paths.append(f'<path class="flat" d="{path(f["geometry"], P, 0.4)}"/>')
badges = []
for n, *_r, pts, _k in STYLES:
    for lon, lat in pts:
        x, y = P(lon, lat)
        badges.append(f'<g class="bd"><circle cx="{x:.0f}" cy="{y:.0f}" r="25"/><text x="{x:.0f}" y="{y+10:.0f}">{n}</text></g>')
cn = lambda lon, lat, t, cls="cn": f'<text class="{cls}" x="{P(lon,lat)[0]:.0f}" y="{P(lon,lat)[1]:.0f}">{t}</text>'
svg = f'''<svg width="{P.w}" height="{P.h}" viewBox="0 0 {P.w} {P.h}">
<defs><pattern id="noinfo" width="12" height="12" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
<rect width="12" height="12" fill="#3b5a6d"/><rect width="4" height="12" fill="#2c4757"/></pattern>
<pattern id="dots" width="16" height="16" patternUnits="userSpaceOnUse"><circle cx="8" cy="8" r="2.6" fill="#0e2130" opacity=".55"/></pattern></defs>
<rect width="100%" height="100%" class="sea"/>{neighbours(P, {"ID"})}
{"".join(paths)}
<image href="{relief(P, 230)}" width="{P.w}" height="{P.h}" class="relief"/>
{cn(97.6,-3.2,"Sumatra","isl")}{cn(109.6,-9.2,"Java","isl")}{cn(111.6,-4.4,"Kalimantan","isl")}{cn(124.6,-3.4,"Sulawesi","isl")}
{cn(121.0,-10.9,"Nusa Tenggara","isl")}
{cn(113.5,3.6,"Malaisie")}{cn(103.8,4.4,"Malaisie")}{cn(126.1,-7.95,"Timor-Leste")}{cn(122.5,5.6,"Philippines")}
{"".join(badges)}
</svg>'''

base_leg = "".join(f'<div class="bl"><i style="background:{c}"></i><b>{l}</b></div>' for l, c, _ in BASE.values())
base_leg += '<div class="bl"><i class="dots" style="background:#e9b07a"></i><b>Tuiles d\'aspect un peu différent</b><small>Kalimantan Sud, Jambi</small></div>'
base_leg += '<div class="bl"><i style="background:repeating-linear-gradient(45deg,#3b5a6d 0 6px,#2c4757 6px 9px)"></i><b>Non traité</b><small>Maluku, Papouasie : peu de couverture</small></div>'
styles = "".join(f'''<div class="sty"><span class="num">{n}</span>{picto(k)}<div><b>{t}</b><small>{z}</small><em>{d}</em></div></div>'''
                 for n, t, z, d, _p, k in STYLES)
html = f'''<!doctype html><meta charset="utf-8"><style>{fonts()}{BASE_CSS}
#card{{width:2700px;padding:44px 50px 30px;display:flex;flex-direction:column;gap:24px}}
.map{{border-radius:8px;overflow:hidden}}
.st{{stroke:#0e2130;stroke-width:1;stroke-linejoin:round}} .flat{{fill:url(#dots);stroke:none}}
.isl{{font-family:ui;font-weight:600;font-size:34px;fill:#8ea6b4;text-anchor:middle;letter-spacing:.12em;text-transform:uppercase}}
.bd circle{{fill:#0e2130;stroke:#f2c94c;stroke-width:4}} .bd text{{font-family:ui;font-weight:600;font-size:30px;fill:#f2c94c;text-anchor:middle}}
.cols{{display:grid;grid-template-columns:700px 1fr;gap:50px}}
h3{{margin:0 0 14px;font-size:32px;color:#f2c94c;font-weight:600}}
.bl{{display:grid;grid-template-columns:44px 1fr;column-gap:14px;align-items:center;margin-bottom:12px}}
.bl i{{grid-row:span 2;width:44px;height:30px;border-radius:5px}} .bl i.dots{{background-image:radial-gradient(#0e2130 25%,transparent 28%)!important;background-size:10px 10px}}
.bl b{{font-size:27px;font-weight:600}} .bl small{{font-family:txt;font-size:20px;color:#8ea6b4}}
.note{{font-family:txt;font-size:20px;color:#8ea6b4;margin-top:14px;line-height:1.4}}
.grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:16px 26px}}
.sty{{display:grid;grid-template-columns:44px 110px 1fr;gap:12px;align-items:center}}
.num{{width:44px;height:44px;border-radius:50%;border:3px solid #f2c94c;color:#f2c94c;font-size:26px;font-weight:600;display:grid;place-items:center}}
.sty b{{display:block;font-size:26px;font-weight:600;line-height:1.1}} .sty small{{display:block;font-size:20px;color:#f2c94c;margin-top:2px}}
.sty em{{display:block;font-style:normal;font-family:txt;font-size:18px;color:#c8d6de;margin-top:2px}}
</style><div id="card"><h1>Toits<span>Indonésie · matériau dominant et styles locaux</span></h1>
<div class="map">{svg}</div>
<div class="cols"><div><h3>Couleur = matériau du toit (vaut presque partout)</h3>{base_leg}
<div class="note">Gradient nord–sud : plus on monte vers le nord, plus la tôle remplace la tuile. Les limites entre provinces sont approximatives.</div></div>
<div><h3>Styles locaux (pastilles numérotées)</h3><div class="grid">{styles}</div></div></div>
<div class="foot">Atlas TGM · d'après Plonk It (Indonésie), reformulé · schémas simplifiés, à comparer aux photos de Plonk It · sommets de poteaux : voir la carte de Plonk It · fond : Natural Earth</div></div>'''
out = os.path.join(os.path.dirname(__file__), "indonesia")
open(out + ".html", "w", encoding="utf-8").write(html)
render(out + ".html", out + ".png")
print("ok", P.w, P.h)
