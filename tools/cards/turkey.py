"""Fiche Turquie : codes de province (plaques + bornes des routes provinciales).
Sources recoupées : Wikipedia EN « Vehicle registration plates of Turkey » et « Provinces of Turkey » (codes, régions NUTS 1),
Plonk It Turquie (bornes kilométriques, ordre alphabétique, indices régionaux). Les codes NE (ISO 3166-2:TR) sont vérifiés contre la liste."""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from cardlib import *

# code : (nom, région NUTS 1) — Wikipedia « Provinces of Turkey »
PROV = {
 1:("Adana","MED"),2:("Adıyaman","SEA"),3:("Afyonkarahisar","EGE"),4:("Ağrı","NEA"),5:("Amasya","WBS"),6:("Ankara","WAN"),
 7:("Antalya","MED"),8:("Artvin","EBS"),9:("Aydın","EGE"),10:("Balıkesir","WMA"),11:("Bilecik","EMA"),12:("Bingöl","CEA"),
 13:("Bitlis","CEA"),14:("Bolu","EMA"),15:("Burdur","MED"),16:("Bursa","EMA"),17:("Çanakkale","WMA"),18:("Çankırı","WBS"),
 19:("Çorum","WBS"),20:("Denizli","EGE"),21:("Diyarbakır","SEA"),22:("Edirne","WMA"),23:("Elazığ","CEA"),24:("Erzincan","NEA"),
 25:("Erzurum","NEA"),26:("Eskişehir","EMA"),27:("Gaziantep","SEA"),28:("Giresun","EBS"),29:("Gümüşhane","EBS"),30:("Hakkari","CEA"),
 31:("Hatay","MED"),32:("Isparta","MED"),33:("Mersin","MED"),34:("İstanbul","IST"),35:("İzmir","EGE"),36:("Kars","NEA"),
 37:("Kastamonu","WBS"),38:("Kayseri","CAN"),39:("Kırklareli","WMA"),40:("Kırşehir","CAN"),41:("Kocaeli","EMA"),42:("Konya","WAN"),
 43:("Kütahya","EGE"),44:("Malatya","CEA"),45:("Manisa","EGE"),46:("Kahramanmaraş","MED"),47:("Mardin","SEA"),48:("Muğla","EGE"),
 49:("Muş","CEA"),50:("Nevşehir","CAN"),51:("Niğde","CAN"),52:("Ordu","EBS"),53:("Rize","EBS"),54:("Sakarya","EMA"),
 55:("Samsun","WBS"),56:("Siirt","SEA"),57:("Sinop","WBS"),58:("Sivas","CAN"),59:("Tekirdağ","WMA"),60:("Tokat","WBS"),
 61:("Trabzon","EBS"),62:("Tunceli","CEA"),63:("Şanlıurfa","SEA"),64:("Uşak","EGE"),65:("Van","CEA"),66:("Yozgat","CAN"),
 67:("Zonguldak","WBS"),68:("Aksaray","CAN"),69:("Bayburt","NEA"),70:("Karaman","WAN"),71:("Kırıkkale","CAN"),72:("Batman","SEA"),
 73:("Şırnak","SEA"),74:("Bartın","WBS"),75:("Ardahan","NEA"),76:("Iğdır","NEA"),77:("Yalova","EMA"),78:("Karabük","WBS"),
 79:("Kilis","SEA"),80:("Osmaniye","MED"),81:("Düzce","EMA"),
}
REG = {  # NUTS 1 : libellé FR, couleur
 "IST":("İstanbul","#e35d6a"),"WMA":("Marmara Ouest","#e8a54b"),"EMA":("Marmara Est","#d9cf55"),"EGE":("Égée","#4fb3d9"),
 "MED":("Méditerranée","#3fbfa0"),"WAN":("Anatolie Ouest","#c7a37a"),"CAN":("Anatolie centrale","#e3c89a"),
 "WBS":("Mer Noire Ouest","#7fc77a"),"EBS":("Mer Noire Est","#3f9a5f"),"NEA":("Anatolie Nord-Est","#a58ee6"),
 "CEA":("Anatolie Centre-Est","#d77fbf"),"SEA":("Anatolie Sud-Est","#e07a4f"),
}
OLD = {33:"İçel", 46:"Maraş", 63:"Urfa"}
CLUES = [  # Plonk It Turquie, reformulé ; (codes concernés, texte)
 ([6], "Ankara : plaques de rue bleues au sommet légèrement arrondi"),
 ([35], "İzmir : plaques de rue bleu foncé, bombées, souvent avec l'emblème d'İzmir en blanc"),
 ([10, 36], "Chevrons jaune sur noir : surtout autour de Balıkesir (ouest) et de Kars (extrême est)"),
 ([50], "Nevşehir : bâtiments en gros blocs de grès clair, de teinte inégale"),
]

feats = admin1("TR")
codes = {int(f["properties"]["iso_3166_2"].split("-")[1]): f for f in feats}
assert sorted(codes) == list(range(1, 82)), "codes NE incomplets"
import unicodedata
flat = lambda t: "".join(ch for ch in unicodedata.normalize("NFKD", t.replace("ı", "i").replace("İ", "I")) if not unicodedata.combining(ch)).lower()[:3]
for c, f in codes.items():   # contrôle croisé des noms NE (sans accents) avec la liste Wikipedia
    a, b = flat(f["properties"]["name"]), flat(PROV[c][0])
    assert a == b or c in (46, 71, 67), (c, f["properties"]["name"], PROV[c][0])

P = Proj(25.55, 45.0, 35.75, 42.25, 2600)
fills, labels, stars = [], [], []
clue_codes = {c for cs, _ in CLUES for c in cs}
for c, f in sorted(codes.items()):
    name, reg = PROV[c]
    fills.append(f'<path class="st" fill="{REG[reg][1]}" d="{path(f["geometry"], P, 0.4)}"/>')
    x, y, area = label_point(f["geometry"], P)
    small = area < 9000
    fs, ns = (28, 0) if small else (38, 17)
    labels.append(f'<text class="code" x="{x:.0f}" y="{y + (fs*0.35 if small else 4):.0f}" style="font-size:{fs}px">{c:02d}</text>')
    if not small:
        labels.append(f'<text class="pn" x="{x:.0f}" y="{y + 24:.0f}">{name}</text>')
    if c in clue_codes:
        stars.append(f'<text class="star" x="{x + (26 if small else 34):.0f}" y="{y - 10:.0f}">★</text>')
nat = "".join(f'<path class="nat" d="{path(f["geometry"], P, 0.4)}"/>' for f in admin0("TR"))
cn = lambda lon, lat, t: f'<text class="cn" x="{P(lon,lat)[0]:.0f}" y="{P(lon,lat)[1]:.0f}">{t}</text>'
svg = f'''<svg width="{P.w}" height="{P.h}" viewBox="0 0 {P.w} {P.h}">
<rect width="100%" height="100%" class="sea"/>{neighbours(P, {"TR"})}
{"".join(fills)}{nat}
<image href="{relief(P, 260)}" width="{P.w}" height="{P.h}" class="relief"/>
{"".join(labels)}{"".join(stars)}
{cn(26.75,42.05,"Bulgarie")}{cn(26.6,39.0,"Grèce")}{cn(43.3,41.9,"Géorgie")}{cn(44.6,40.3,"Arm.")}
{cn(42.5,36.1,"Irak")}{cn(38.6,36.05,"Syrie")}{cn(33.2,35.95,"Chypre")}{cn(34.5,42.0,"Mer Noire")}{cn(30.0,36.0,"Méditerranée")}
</svg>'''

legend = "".join(f'<span class="lg"><i style="background:{c}"></i>{l}</span>' for l, c in REG.values())
table = "".join(f'<span class="tc"><b>{c:02d}</b>{PROV[c][0]}{" <em>(" + OLD[c] + ")</em>" if c in OLD else ""}</span>' for c in range(1, 82))
clues = "".join(f'<li><b>{" · ".join(f"{c:02d}" for c in cs)}</b>{t}</li>' for cs, t in CLUES)
html = f'''<!doctype html><meta charset="utf-8"><style>{fonts()}{BASE_CSS}
#card{{width:2700px;padding:44px 50px 30px;display:flex;flex-direction:column;gap:22px}}
.map{{border-radius:8px;overflow:hidden}}
.st{{stroke:#0e2130;stroke-width:1.1;stroke-linejoin:round}} .nat{{fill:none;stroke:#0e2130;stroke-width:3}}
.code{{font-family:ui;font-weight:600;fill:#0e2130;text-anchor:middle;paint-order:stroke;stroke:#ffffffa8;stroke-width:5px}}
.pn{{font-family:ui;font-size:17px;fill:#0e2130;text-anchor:middle;opacity:.85}}
.star{{font-size:26px;fill:#fff;paint-order:stroke;stroke:#0e2130;stroke-width:4px}}
.legend{{display:flex;flex-wrap:wrap;gap:8px 26px;font-size:26px;color:#c8d6de}} .lg i{{display:inline-block;width:22px;height:22px;border-radius:4px;margin-right:8px;vertical-align:-3px}}
.row{{display:grid;grid-template-columns:1.9fr 1fr;gap:40px}}
.table{{columns:6;column-gap:26px;font-family:txt;font-size:20px;color:#c8d6de}} .tc{{display:block;break-inside:avoid;line-height:1.45}}
.tc b{{display:inline-block;width:34px;color:#f2c94c;font-family:ui;font-size:23px}} .tc em{{color:#8ea6b4;font-style:normal}}
.box{{border-left:4px solid #f2c94c;padding:2px 0 2px 18px}} .box h3{{margin:0 0 6px;font-size:30px;color:#f2c94c;font-weight:600}}
.box p,.box li{{font-family:txt;font-size:21px;color:#c8d6de;margin:0 0 6px}} .box ul{{margin:0;padding-left:0;list-style:none}}
.box li b{{font-family:ui;color:#fff;margin-right:10px}} .box strong{{color:#fff}}
</style><div id="card"><h1>Codes des provinces<span>Turquie · bornes des routes provinciales</span></h1>
<div class="map">{svg}</div>
<div class="legend">{legend}<span class="lg" style="margin-left:auto"><b style="color:#fff">★</b> indice régional ci-dessous</span></div>
<div class="row"><div class="table">{table}</div>
<div style="display:flex;flex-direction:column;gap:22px">
<div class="box"><h3>Où lire le code en partie</h3>
<p><strong>Borne kilométrique, numéro en haut à gauche</strong> : sur une route provinciale il a la forme <strong>03-xx</strong>, et la 1<sup>re</sup> moitié est le code de la province (ici Afyon).</p>
<p>Juste un nombre (360 = D360) : route nationale, pas de province. « O-5 » : autoroute.</p>
<p><strong>Plaques</strong> : même code (34 ABC 123 = İstanbul), mais floutées par Google ; utile seulement quand le flou est raté, et c'est le lieu d'immatriculation, pas ta position.</p></div>
<div class="box"><h3>Mémo de l'ordre</h3>
<p>01–67 : ordre alphabétique des noms de l'époque, d'où Mersin en 33 (İçel), Kahramanmaraş en 46 (Maraş), Şanlıurfa en 63 (Urfa).</p>
<p>68–81 : provinces créées depuis 1989, hors ordre alphabétique.</p></div>
<div class="box"><h3>Indices régionaux ★</h3><ul>{clues}</ul></div>
</div></div>
<div class="foot">Atlas TGM · codes : Wikipedia (plaques, provinces, routes provinciales de Turquie) · bornes : Plonk It et geometas, reformulé · indices : Plonk It · couleurs : régions statistiques NUTS 1 · fond : Natural Earth</div></div>'''
out = os.path.join(os.path.dirname(__file__), "turkey")
open(out + ".html", "w", encoding="utf-8").write(html)
render(out + ".html", out + ".png")
print("ok", P.w, P.h)
