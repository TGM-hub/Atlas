"""Fiches Philippines, une par catégorie : régions/villes, architecture, infrastructures, paysage.
Sources : Plonk It Philippines (citations relevées le 2026-10-03) ; régions 2025 : PhilAtlas (18 régions, dont la
Negros Island Region) et EO 91-2025 (Sulu rattachée à la Région IX). Limites : Natural Earth (provinces avant 2022).
Usage : python philippines.py [ref|arch|infra|land] [--local]   (--local : vignettes Plonk It, fiches « (local) » jamais publiées)"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from cardlib import *
from shapely.geometry import shape, mapping
from shapely.ops import unary_union

REGIONS = [  # (code, nom, couleur, provinces NE)
 ("NCR", "Metro Manila (NCR)", "#e35d6a", ["Caloocan","Las Pinas","Makati","Malabon","Mandaluyong City","Manila","Marikina","Muntinlupa","Navotas","Paranaque","Pasay","Pasig","Pateros","Quezon City","San Juan","Taguig","Valenzuela"]),
 ("CAR", "Cordillère (CAR)", "#a58ee6", ["Abra","Apayao","Benguet","Baguio","Ifugao","Kalinga","Mountain Province"]),
 ("I", "Ilocos (I)", "#e8a54b", ["Ilocos Norte","Ilocos Sur","La Union","Pangasinan","Dagupan"]),
 ("II", "Vallée de Cagayan (II)", "#d9cf55", ["Batanes","Cagayan","Isabela","Santiago","Nueva Vizcaya","Quirino"]),
 ("III", "Luçon central (III)", "#7fc77a", ["Aurora","Bataan","Bulacan","Nueva Ecija","Pampanga","Angeles","Tarlac","Zambales","Olongapo"]),
 ("IV-A", "CALABARZON (IV-A)", "#4fb3d9", ["Batangas","Cavite","Laguna","Quezon","Lucena","Rizal"]),
 ("MIMAROPA", "MIMAROPA", "#3fbfa0", ["Marinduque","Mindoro Occidental","Mindoro Oriental","Palawan","Puerto Princesa","Romblon"]),
 ("V", "Bicol (V)", "#d77fbf", ["Albay","Camarines Norte","Camarines Sur","Naga","Catanduanes","Masbate","Sorsogon"]),
 ("VI", "Visayas occidentales (VI)", "#e3c89a", ["Aklan","Antique","Capiz","Guimaras","Iloilo"]),
 ("NIR", "Île de Negros (NIR)", "#e07a4f", ["Negros Occidental","Bacolod","Negros Oriental","Siquijor"]),
 ("VII", "Visayas centrales (VII)", "#8fb3c9", ["Bohol","Cebu","Mandaue","Lapu-Lapu"]),
 ("VIII", "Visayas orientales (VIII)", "#c7a37a", ["Biliran","Eastern Samar","Leyte","Tacloban","Ormoc","Northern Samar","Samar","Southern Leyte"]),
 ("IX", "Péninsule de Zamboanga (IX)", "#7fc77a", ["Zamboanga del Norte","Zamboanga del Sur","Zamboanga","Zamboanga Sibugay","Sulu"]),
 ("X", "Mindanao du Nord (X)", "#e8a54b", ["Bukidnon","Camiguin","Lanao del Norte","Iligan","Misamis Occidental","Misamis Oriental","Cagayan de Oro"]),
 ("XI", "Davao (XI)", "#4fb3d9", ["Compostela Valley","Davao del Norte","Davao del Sur","Davao","Davao Oriental"]),
 ("XII", "SOCCSKSARGEN (XII)", "#d9cf55", ["Cotabato@SOCCSKSARGEN (Region XII)","South Cotabato","General Santos","Sarangani","Sultan Kudarat"]),
 ("XIII", "Caraga (XIII)", "#d77fbf", ["Agusan del Norte","Butuan","Agusan del Sur","Surigao del Norte","Surigao del Sur"]),
 ("BARMM", "Bangsamoro (BARMM)", "#a58ee6", ["Basilan","Lanao del Sur","Maguindanao","Tawi-Tawi","Cotabato@Autonomous Region in Muslim Mindanao (ARMM)"]),
]
RENAME = {"Compostela Valley": "Davao de Oro", "Mindoro Occidental": "Occidental Mindoro", "Mindoro Oriental": "Oriental Mindoro",
          "Maguindanao": "Maguindanao (N. et S.)"}
CITIES = [  # villes principales (lon, lat, nom, côté) — repère pour placer un guess
 (120.98,14.6,"Manille","l"),(120.59,16.41,"Baguio","r"),(120.59,18.2,"Laoag","r"),(120.39,17.57,"Vigan","l"),
 (120.34,16.04,"Dagupan","l"),(121.73,17.61,"Tuguegarao","r"),(121.55,16.69,"Santiago","r"),(120.59,15.15,"Angeles","l"),
 (120.97,15.49,"Cabanatuan","r"),(121.06,13.76,"Batangas","l"),(121.62,13.94,"Lucena","r"),(123.18,13.62,"Naga","r"),
 (123.74,13.14,"Legazpi","r"),(118.74,9.74,"Puerto Princesa","r"),(121.18,13.41,"Calapan","r"),(122.56,10.72,"Iloilo","l"),
 (122.75,11.58,"Roxas","r"),(122.95,10.68,"Bacolod","r"),(123.31,9.31,"Dumaguete","r"),(123.89,10.31,"Cebu","r"),
 (123.85,9.65,"Tagbilaran","r"),(125.0,11.24,"Tacloban","r"),(122.08,6.91,"Zamboanga","r"),(123.34,8.59,"Dipolog","l"),
 (124.65,8.48,"Cagayan de Oro","r"),(124.24,8.23,"Iligan","l"),(125.54,8.95,"Butuan","r"),(125.49,9.79,"Surigao","r"),
 (125.61,7.07,"Davao","r"),(125.17,6.11,"General Santos","r"),(124.25,7.22,"Cotabato","l"),(123.62,12.37,"Masbate","r"),
]

feats = admin1("PH")
key_of = lambda f: f["properties"]["name"] if f["properties"]["name"] != "Cotabato" else "Cotabato@" + f["properties"]["region"]
REG_OF = {p: r for r, _n, _c, ps in REGIONS for p in ps}
missing = [key_of(f) for f in feats if key_of(f) not in REG_OF]
assert not missing, missing
P = Proj(116.8, 127.0, 4.4, 21.3, 1560)

def regions_outline():
    groups = {}
    for f in feats: groups.setdefault(REG_OF[key_of(f)], []).append(shape(f["geometry"]).buffer(0.002))
    return "".join(f'<path class="rg" d="{path(mapping(unary_union(g).buffer(-0.002)), P, 0.3)}"/>' for g in groups.values())
def provinces(fill_fn):
    return "".join(f'<path class="st" fill="{fill_fn(f)}" d="{path(f["geometry"], P, 0.3)}"/>' for f in feats)
def cities(lst=CITIES, big=False):
    out = []
    for lon, lat, n, side in lst:
        x, y = P(lon, lat); dx = 10 if side == "r" else -10
        out.append(f'<circle class="ct" cx="{x:.0f}" cy="{y:.0f}" r="{6 if big else 5}"/><text class="ctl{" big" if big else ""}" x="{x+dx:.0f}" y="{y+7:.0f}" text-anchor="{"start" if side=="r" else "end"}">{n}</text>')
    return "".join(out)
def badge(n, lon, lat, tri=False):
    x, y = P(lon, lat)
    sh = (f'<path d="M{x:.0f},{y-28:.0f}L{x+26:.0f},{y+17:.0f}L{x-26:.0f},{y+17:.0f}Z"/>' if tri else f'<circle cx="{x:.0f}" cy="{y:.0f}" r="23"/>')
    return f'<g class="bd{" tri" if tri else ""}">{sh}<text x="{x:.0f}" y="{y + (13 if tri else 10):.0f}">{n}</text></g>'
cn = lambda lon, lat, t, cls="isl": f'<text class="{cls}" x="{P(lon,lat)[0]:.0f}" y="{P(lon,lat)[1]:.0f}">{t}</text>'
ISLANDS = f'{cn(119.0,17.3,"Luçon")}{cn(119.0,11.4,"Palawan")}{cn(126.2,12.6,"Visayas")}{cn(126.1,4.9,"Mindanao")}{cn(118.2,5.3,"Malaisie","cn")}'
CSS = f"""{fonts()}{BASE_CSS}
#card{{width:2700px;padding:44px 50px 30px;display:grid;grid-template-columns:{P.w}px 1fr;gap:20px 50px}}
h1{{grid-column:1/-1}} .map{{border-radius:8px;overflow:hidden;height:{P.h}px}} .foot{{grid-column:1/-1}}
.st{{stroke:#0e2130;stroke-width:.7;stroke-linejoin:round}} .rg{{fill:none;stroke:#0e2130;stroke-width:2.6;stroke-linejoin:round}}
.isl{{font-family:ui;font-weight:600;font-size:40px;fill:#8ea6b4;text-anchor:middle;letter-spacing:.12em;text-transform:uppercase}}
.ct{{fill:#fff;stroke:#0e2130;stroke-width:2.5}} .ctl{{font-family:ui;font-weight:600;font-size:20px;fill:#fff;paint-order:stroke;stroke:#0e2130;stroke-width:4.5px;stroke-linejoin:round}}
.ctl.big{{font-size:23px}}
.pn{{font-family:ui;font-weight:600;font-size:17px;fill:#0e2130;text-anchor:middle;paint-order:stroke;stroke:#ffffff80;stroke-width:3px}}
.bd circle,.bd path{{fill:#0e2130;stroke:#f2c94c;stroke-width:4}} .bd text{{font-family:ui;font-weight:600;font-size:27px;fill:#f2c94c;text-anchor:middle}}
.bd.tri path{{stroke:#fff}} .bd.tri text{{fill:#fff;font-size:23px}}
.chip rect{{fill:#fff;stroke:#0e2130;stroke-width:2}} .chip text{{font-family:ui;font-weight:600;font-size:23px;fill:#0e2130;text-anchor:middle}}
.side{{display:flex;flex-direction:column;gap:30px}} h3{{margin:0 0 14px;font-size:32px;color:#f2c94c;font-weight:600}}
.bl,.it{{display:grid;grid-template-columns:48px 1fr;gap:14px;align-items:center;margin-bottom:14px}} .bl i{{width:48px;height:34px;border-radius:5px}}
.bl b,.it b{{display:block;font-size:28px;font-weight:600;line-height:1.1}} .bl small,.it small{{display:block;font-family:txt;font-size:21px;color:#8ea6b4;margin-top:3px}}
.num{{width:44px;height:44px;border-radius:50%;border:3px solid #f2c94c;color:#f2c94c;font-size:25px;font-weight:600;display:grid;place-items:center}}
.num.tri{{border-radius:6px;border-color:#fff;color:#fff}}
.note{{font-family:txt;font-size:21px;color:#8ea6b4;line-height:1.45}}
.rl{{display:grid;grid-template-columns:30px 1fr;gap:10px;margin-bottom:9px;font-size:24px}} .rl i{{width:30px;height:22px;border-radius:4px;margin-top:4px}}
.rl small{{display:block;font-family:txt;font-size:18px;color:#8ea6b4}}"""
NEUTRAL = "#7f93a3"

def page(title, svg_inner, side, foot):
    svg = f'''<svg width="{P.w}" height="{P.h}" viewBox="0 0 {P.w} {P.h}"><rect width="100%" height="100%" class="sea"/>{neighbours(P, {"PH"})}
{svg_inner}</svg>'''
    return f'''<!doctype html><meta charset="utf-8"><style>{CSS}</style><div id="card"><h1>{title[0]}<span>{title[1]}</span></h1>
<div class="map">{svg}</div><div class="side">{side}</div><div class="foot">{foot}</div></div>'''

RELIEF = None
def relief_img():
    global RELIEF
    if RELIEF is None: RELIEF = relief(P, 200)
    return f'<image href="{RELIEF}" width="{P.w}" height="{P.h}" class="relief"/>'

import base64, io
LOCAL = "--local" in sys.argv
PHOTOS = os.environ.get("PLONKIT_DIR", "/mnt/user-data/uploads/Atlas/_private_cache/plonkit/philippines")
def photo(name):
    if not LOCAL or not name: return ""
    from PIL import Image
    im = Image.open(os.path.join(PHOTOS, name)).convert("RGB"); im.thumbnail((420, 220))
    b = io.BytesIO(); im.save(b, "JPEG", quality=85)
    return f'<img class="ph" src="data:image/jpeg;base64,{base64.b64encode(b.getvalue()).decode()}">'
def row(mark, title, sub, ph=None):
    """mark : ('n','1') pastille ronde, ('t','A') triangle, ('c','#hex') aplat de couleur."""
    k, v = mark
    m = {"n": f'<span class="num">{v}</span>', "t": f'<span class="num tri">{v}</span>', "c": f'<i class="sw" style="background:{v}"></i>'}[k]
    return f'<div class="row{" wp" if LOCAL and ph else ""}">{m}<div><b>{title}</b><small>{sub}</small></div>{photo(ph)}</div>'
CSS += """
.row{display:grid;grid-template-columns:48px 1fr;gap:16px;align-items:center;margin-bottom:14px}
.row.wp{grid-template-columns:48px 1fr 420px}
.row b{display:block;font-size:28px;font-weight:600;line-height:1.12} .row small{display:block;font-family:txt;font-size:21px;color:#8ea6b4;margin-top:4px}
.sw{width:48px;height:34px;border-radius:5px} .ph{width:420px;border-radius:6px;display:block}"""
SUFFIX = " (local)" if LOCAL else ""
FOOT_PH = " · photos : Plonk It (usage personnel, non publié)" if LOCAL else ""

def card_ref():
    col = {r: c for r, _n, c, _p in REGIONS}
    labels, placed = [], []
    for lon, lat, n, side in CITIES:
        x, y = P(lon, lat); w = len(n) * 12
        placed.append((x - 8, y - 12, x + w + 12, y + 10) if side == "r" else (x - w - 12, y - 12, x + 8, y + 10))
    provs = sorted([f for f in feats if f["properties"]["type_en"] == "Province"], key=lambda f: -shape(f["geometry"]).area)
    for f in provs:
        nm = RENAME.get(f["properties"]["name"], f["properties"]["name"])
        x, y, a = label_point(f["geometry"], P)
        for dy in (0, -18, 18, -32, 32):
            w = len(nm) * 8.4; bx = (x - w / 2, y + dy - 8, x + w / 2, y + dy + 8)
            if all(bx[2] < b[0] or bx[0] > b[2] or bx[3] < b[1] or bx[1] > b[3] for b in placed):
                placed.append(bx); labels.append(f'<text class="pn" x="{x:.0f}" y="{y+dy+6:.0f}">{nm}</text>'); break
    inner = provinces(lambda f: col[REG_OF[key_of(f)]]) + regions_outline() + relief_img() + "".join(labels) + cities(big=True) + ISLANDS
    prov_names = {x["properties"]["name"] for x in feats if x["properties"]["type_en"] == "Province"}
    def plist(r, ps):
        if r == "NCR": return "16 villes et Pateros"
        return ", ".join("Cotabato" if p.startswith("Cotabato@SOCC") else RENAME.get(p, p) for p in ps if p in prov_names or p.startswith("Cotabato@SOCC"))
    groups = [("Luçon", REGIONS[:8]), ("Visayas", REGIONS[8:12]), ("Mindanao", REGIONS[12:])]
    side = '<div><h3>Où lire le lieu en partie</h3>' + row(("n", "?"), "Noms de province, très fréquents sur les panneaux",
            "Absents de la carte du jeu : il faut les connaître (Davao de Oro = ex-Compostela Valley)") + \
        row(("n", "?"), "Boîtiers noirs ou blancs sur les poteaux",
            "Code de 3 lettres = la municipalité (ou 2 lettres municipalité + 1 lettre province) ; ex. GMI = Gamu (Isabela)", "2_blackwhiteboxes.png") + '</div>'
    side += "".join(f'<div><h3>{g}</h3>' + "".join(
        f'<div class="rl"><i style="background:{c}"></i><div>{n}<small>{plist(r, ps)}</small></div></div>' for r, n, c, ps in rs) + '</div>' for g, rs in groups)
    side += '<div class="note">18 régions (2025) : Negros Island Region recréée en 2024, Sulu rattachée à la Région IX en 2025. Davao Occidental est incluse dans Davao del Sur sur ce fond de carte.</div>'
    return page(("Régions, provinces et villes", "Philippines"), inner, side,
                "Atlas TGM · régions : PhilAtlas, EO 91-2025 · indices : d'après Plonk It · limites et fond : Natural Earth" + FOOT_PH)

def card_arch():
    zone = lambda f: "pal" if f["properties"]["name"] in ("Palawan", "Puerto Princesa") else (
        "south" if REG_OF[key_of(f)] in {"VI","NIR","VII","VIII","IX","X","XI","XII","XIII","BARMM"} else "north")
    Z = {"south": "#5fb8a6", "pal": "#e3a35a", "north": NEUTRAL}
    inner = provinces(lambda f: Z[zone(f)]) + regions_outline() + relief_img() + cities() + ISLANDS
    inner += badge("1", 121.15, 17.95) + badge("2", 123.6, 7.6) + badge("A", 121.95, 13.4, True) + badge("B", 124.29, 7.75, True)
    side = '<div><h3>Couleur = murs en bambou tressé (amakan)</h3>' + \
        row(("c", Z["south"]), "Tressage en losanges", "Presque uniquement dans la moitié sud : Visayas et Mindanao", "2_diamondpatternhouse.png") + \
        row(("c", Z["pal"]), "Tressage en diagonale (sawali)", "Surtout Palawan ; existe aussi au nord, où on l’appelle sawali", "2_palawanpatternhouse.png") + \
        row(("c", NEUTRAL), "Losanges quasi absents", "Luçon et Mindoro") + \
        '<div class="note">La limite entre « nord » et « moitié sud » est approximative.</div></div>'
    side += '<div><h3>Indices de zone</h3>' + \
        row(("n", "1"), "Décorations en bouteilles de Mountain Dew vert fluo", "Dans le nord, surtout au nord de Luçon", "2_mountaindew.png") + \
        row(("n", "2"), "Mosquées, région à majorité musulmane", "Une partie de l’ouest de Mindanao (le reste du pays est très chrétien)", "2_islam.png") + '</div>'
    side += '<div><h3>Repères ponctuels</h3>' + \
        row(("t", "A"), "Statues et images de soldats romains", "Île de Marinduque", "3_marinduqueromansoldier.png") + \
        row(("t", "B"), "Maisons détruites, ruines du siège de 2017", "Marawi et alentours", "3_marawiruins.png") + '</div>'
    return page(("Architecture", "Philippines"), inner, side, "Atlas TGM · d'après Plonk It (Philippines), reformulé · limites et fond : Natural Earth" + FOOT_PH)

def card_infra():
    inner = provinces(lambda f: NEUTRAL) + regions_outline() + relief_img() + cities() + ISLANDS
    B = [("1", "Glissières en béton rayées jaune et noir", "Cordillère (CAR)", [(121.0, 17.05)], "2_baguioconcreteguardrail.png"),
         ("2", "Glissières blanches à trois bandes noires", "Bicol, propres à la région", [(123.0, 13.95)], "2_bicolguardrail.png"),
         ("3", "Poteaux carrés en béton, encoche sur deux faces", "Surtout au nord de Manille et autour de Bacolod", [(120.65, 15.75), (123.2, 10.45)], "2_chilepole.png"),
         ("4", "Sommet de poteau à deux hautes barres en L", "Manille et environs, propre à la zone", [(121.45, 14.45)], "2_manilapoletop.png"),
         ("5", "Poteaux en treillis métallique carré", "Mindanao, surtout péninsule de Zamboanga", [(122.6, 7.75)], "2_zamboangapole.png"),
         ("6", "Lampadaires jaunes, bandes noires en bas", "Siquijor", [(123.55, 9.0)], "3_siquijorlamp.png"),
         ("7", "Route très large (souvent 6 voies), peu de trafic, double fil électrique", "Au sud de Puerto Princesa (Palawan)", [(118.4, 9.35)], "3_trans-palawanhighway.png"),
         ("8", "Grandes bornes blanches décorées (Marche de la mort de Bataan)", "De Mariveles / Bagac à San Fernando", [(120.25, 14.55)], "3_bataandeathmarchstone.png"),
         ("9", "Tracteur kuliglig", "Surtout dans les plaines autour de Cauayan (Isabela)", [(122.15, 16.95)], "2_cambocar.png")]
    inner += "".join(badge(n, lo, la) for n, _t, _l, pts, _p in B for lo, la in pts)
    side = '<div><h3>Poteaux, glissières, routes, véhicules</h3>' + "".join(row(("n", n), t, l, ph) for n, t, l, _, ph in B) + '</div>'
    side += '<div class="note">Boîtiers à code de municipalité : voir la fiche des régions. Tricycles et plaques de moto : cartes de Plonk It.</div>'
    return page(("Infrastructures", "Philippines"), inner, side, "Atlas TGM · d'après Plonk It (Philippines), reformulé · limites et fond : Natural Earth" + FOOT_PH)

def card_land():
    crop = {"corn": "#e9cf5a", "cane": "#7fc77a", "mind": "#e3a35a"}
    def fill(f):
        r = REG_OF[key_of(f)]
        if r in {"I", "II", "CAR"}: return crop["corn"]
        if f["properties"]["name"] in ("Negros Occidental", "Bacolod", "Negros Oriental", "Iloilo", "Capiz", "Aklan", "Antique", "Guimaras"): return crop["cane"]
        if r in {"IX", "X", "XI", "XII", "XIII", "BARMM"}: return crop["mind"]
        return NEUTRAL
    inner = provinces(fill) + regions_outline() + relief_img() + cities() + ISLANDS
    inner += badge("1", 121.2, 16.95) + badge("2", 125.95, 8.35)
    inner += badge("A", 123.69, 13.26, True) + badge("B", 124.17, 9.83, True) + badge("C", 120.74, 15.2, True)
    side = '<div><h3>Couleur = culture caractéristique</h3>' + \
        row(("c", crop["corn"]), "Maïs", "Présent presque partout ; surtout au nord de Luçon et à Mindanao", "2_corn.png") + \
        row(("c", crop["cane"]), "Canne à sucre", "Surtout Negros et Panay", "2_sugarcane.png") + \
        row(("c", crop["mind"]), "Ananas (Mindanao)", "Plantations surtout à Mindanao", "2_pineapple.png") + \
        row(("c", crop["mind"]), "Palmier à huile (Mindanao)", "La grande majorité à Mindanao", "2_oilpalms.png") + \
        row(("c", crop["mind"]), "Bananes (centre et sud de Mindanao)", "Presque uniquement là", "2_banana.png") + \
        '<div class="note">La couleur résume la culture la plus caractéristique de la zone selon Plonk It ; ce n’est pas une carte de production.</div></div>'
    side += '<div><h3>Végétation et relief</h3>' + \
        row(("n", "1"), "Montagnes boisées, flancs assez secs, beaucoup de pins", "Nord de Luçon (rare : routes d’altitude à Mindanao)", "2_luzonmountain.png") + \
        row(("n", "2"), "Albizia des Moluques : tronc clair, feuilles pennées en haut", "Mindanao, surtout le centre et l'est", "2_mindanaotree.png") + \
        row(("t", "A"), "Volcan Mayon, cône presque parfait", "Albay (Bicol)", "3_mayonvolcano.png") + \
        row(("t", "B"), "Chocolate Hills, collines rondes herbeuses", "Centre de Bohol", "3_chocolatehills.png") + \
        row(("t", "C"), "Mont Arayat isolé dans une plaine agricole", "Pampanga (Luçon central)", "3_arayatvolcano.png") + '</div>'
    return page(("Paysage et cultures", "Philippines"), inner, side, "Atlas TGM · d'après Plonk It (Philippines), reformulé · limites et fond : Natural Earth" + FOOT_PH)

CARDS = {"ref": card_ref, "arch": card_arch, "infra": card_infra, "land": card_land}
for k in ([a for a in sys.argv[1:] if not a.startswith("--")] or CARDS):
    out = os.path.join(os.path.dirname(__file__), f"ph_{k}{'_local' if LOCAL else ''}")
    open(out + ".html", "w", encoding="utf-8").write(CARDS[k]())
    render(out + ".html", out + ".png")
    print("ok", k, SUFFIX)
