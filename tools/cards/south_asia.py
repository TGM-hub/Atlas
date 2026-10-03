import json, math, base64, io, os, sys
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter
sys.path.insert(0, os.path.dirname(__file__))
from south_asia_data import SCRIPTS, IN, LK_TAMIL, LK_MIXED, NOTES, LABELS, CITIES, CITIES_LK
D = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
Image.MAX_IMAGE_PIXELS = None
COL = {k: c for k, _, c, *_ in SCRIPTS}

# ---- relief (Natural Earth shaded relief, équirectangulaire) ----
rgb = Image.open(f"{D}/bm/shadedrelief.jpg"); SW, SH = rgb.size
def relief_crop(lon0, lon1, lat0, lat1, w, h):
    x0, x1 = int((lon0 + 180) / 360 * SW), int((lon1 + 180) / 360 * SW)
    y0, y1 = int((90 - lat1) / 180 * SH), int((90 - lat0) / 180 * SH)
    a = np.asarray(rgb.crop((x0, y0, x1, y1)), dtype=np.int16)
    land = ~((a[..., 2] > a[..., 0] + 18) & (a[..., 2] > a[..., 1]))
    L = a.mean(-1).astype(np.float32) + 1; m = land.astype(np.float32)
    B = gaussian_filter(L * m, 10) / np.maximum(gaussian_filter(m, 10), 1e-3)
    g = np.where(land, L / np.maximum(B, 1), 1.0)
    g = np.clip(128 + (g - 1) * 380, 0, 255).astype(np.uint8)
    im = Image.fromarray(g, "L").resize((w, h), Image.LANCZOS)
    buf = io.BytesIO(); im.save(buf, "PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()

# ---- géométrie ----
a0 = json.load(open(f"{D}/ne50_admin0.geojson"))
a1 = json.load(open(f"{D}/ne10_admin1.geojson"))
K = math.cos(math.radians(21))
class Proj:
    def __init__(s, lon0, lon1, lat0, lat1, w):
        s.lon0, s.lat1 = lon0, lat1; s.k = w / ((lon1 - lon0) * K)
        s.w, s.h = w, round((lat1 - lat0) * s.k); s.box = (lon0, lon1, lat0, lat1)
    def __call__(s, lon, lat): return ((lon - s.lon0) * K * s.k, (s.lat1 - lat) * s.k)
def rings(g):
    return g["coordinates"] if g["type"] == "Polygon" else [r for p in g["coordinates"] for r in p]
def path(g, P, simplify=0.6):
    out = []
    for r in rings(g):
        pts, last = [], None
        for lon, lat in r:
            x, y = P(lon, lat)
            if last and abs(x - last[0]) + abs(y - last[1]) < simplify: continue
            pts.append(f"{x:.1f},{y:.1f}"); last = (x, y)
        if len(pts) > 2: out.append("M" + "L".join(pts) + "Z")
    return "".join(out)

def layer(P, focus):
    lon0, lon1, lat0, lat1 = P.box
    def inside(f):
        bb = f.get("bbox")
        return True
    s = []
    for f in a0["features"]:
        iso = f["properties"]["ISO_A2_EH"]
        if iso in focus: continue
        s.append(f'<path class="nb" d="{path(f["geometry"], P)}"/>')
    for f in a1["features"]:
        p = f["properties"]; iso = p["iso_a2"]
        if iso not in focus: continue
        name = p["name"]
        if iso == "IN": key, fill = IN[name], COL[IN[name]]
        elif iso == "BD": key, fill = "beng", COL["beng"]
        else:
            key = "taml" if name in LK_TAMIL else "mix" if name in LK_MIXED else "sinh"
            fill = "url(#mix)" if key == "mix" else COL[key]
        s.append(f'<path class="st" fill="{fill}" d="{path(f["geometry"], P, 0.3)}"><title>{name}</title></path>')
    for f in a0["features"]:                       # frontières nationales par-dessus les États
        if f["properties"]["ISO_A2_EH"] in focus:
            s.append(f'<path class="nat" d="{path(f["geometry"], P, 0.3)}"/>')
    return "\n".join(s)

P = Proj(66, 97.6, 5.5, 37.3, 1720)
I = Proj(79.4, 82.1, 5.75, 10.0, 320)
FOCUS = {"IN", "BD", "LK"}
def cities(lst, Pp):
    out = []
    for lon, lat, n, side in lst:
        x, y = Pp(lon, lat); dx = 11 if side == "r" else -11
        out.append(f'<circle class="ct" cx="{x:.0f}" cy="{y:.0f}" r="5"/><text class="ctl" x="{x+dx:.0f}" y="{y+7:.0f}" text-anchor="{"start" if side=="r" else "end"}">{n}</text>')
    return "".join(out)
def lab(k, lon, lat, t, Pp):
    x, y = Pp(lon, lat); return f'<text class="lb" x="{x:.0f}" y="{y:.0f}">{t}</text>'
main = f'''<svg width="{P.w}" height="{P.h}" viewBox="0 0 {P.w} {P.h}">
<defs><pattern id="mix" width="14" height="14" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
<rect width="14" height="14" fill="{COL['sinh']}"/><rect width="7" height="14" fill="{COL['taml']}"/></pattern></defs>
<rect width="100%" height="100%" class="sea"/>
{layer(P, FOCUS)}
<image href="{relief_crop(*P.box, P.w, P.h)}" width="{P.w}" height="{P.h}" class="relief"/>
{cities(CITIES, P)}
{''.join(lab(*l, P) for l in LABELS)}
<text class="cn" x="{P(69.5,29.5)[0]:.0f}" y="{P(69.5,29.5)[1]:.0f}">Pakistan</text>
<text class="cn" x="{P(83.6,28.6)[0]:.0f}" y="{P(83.6,28.6)[1]:.0f}">Népal</text>
<text class="cn" x="{P(90.4,27.9)[0]:.0f}" y="{P(90.4,27.9)[1]:.0f}">Bhoutan</text>
<text class="cn" x="{P(85,34)[0]:.0f}" y="{P(85,34)[1]:.0f}">Chine</text>
<text class="cn" x="{P(95.6,21)[0]:.0f}" y="{P(95.6,21)[1]:.0f}">Myanmar</text>
</svg>'''
inset = f'''<svg width="{I.w}" height="{I.h}" viewBox="0 0 {I.w} {I.h}">
<rect width="100%" height="100%" class="sea"/>
{layer(I, {"LK"})}
<image href="{relief_crop(*I.box, I.w, I.h)}" width="{I.w}" height="{I.h}" class="relief"/>
{cities(CITIES_LK, I)}
<text class="lb sm" x="{I(80.45,9.05)[0]:.0f}" y="{I(80.45,9.05)[1]:.0f}">Tamoul</text>
<text class="lb sm" x="{I(80.45,7.75)[0]:.0f}" y="{I(80.45,7.75)[1]:.0f}">Cinghalais</text>
</svg>'''

FONTS = {"deva":"noto-sans-devanagari-devanagari","guru":"noto-sans-gurmukhi-gurmukhi","guj":"noto-sans-gujarati-gujarati",
 "beng":"noto-sans-bengali-bengali","orya":"noto-sans-oriya-oriya","telu":"noto-sans-telugu-telugu","knda":"noto-sans-kannada-kannada",
 "taml":"noto-sans-tamil-tamil","mlym":"noto-sans-malayalam-malayalam","mtei":"noto-sans-meetei-mayek-meetei-mayek",
 "sinh":"noto-sans-sinhala-sinhala","arab":"noto-naskh-arabic-arabic"}
def fface(fam, base, w):
    for dp, _, fs in os.walk(f"{D}/fonts"):
        for f in fs:
            if f == f"{base}-{w}-normal.woff2":
                return f"@font-face{{font-family:{fam};font-weight:{w};src:url(data:font/woff2;base64,{base64.b64encode(open(os.path.join(dp,f),'rb').read()).decode()})}}"
    raise SystemExit(f"police manquante {base}")
css_fonts = "".join(fface(f"s_{k}", b, 600) for k, b in FONTS.items())
css_fonts += fface("ui", "barlow-condensed-latin", 600) + fface("ui", "barlow-condensed-latin", 400) + fface("ui", "barlow-condensed-latin-ext", 400) + fface("ui", "barlow-condensed-latin-ext", 600)
css_fonts += fface("txt", "barlow-latin", 400) + fface("txt", "barlow-latin-ext", 400)

rows = "".join(f'''<div class="row"><span class="sw" style="background:{c}"></span>
<div class="nm"><b>{lbl}</b><small>{where}</small><em>{cue}</em></div>
<span class="smp" style="font-family:s_{fnt},ui">{smp}</span></div>''' for k, lbl, c, smp, fnt, where, cue in SCRIPTS)
notes = "".join(f'<div class="note"><b>{t}</b><span>{x}</span></div>' for t, x in NOTES)
html = f'''<!doctype html><meta charset="utf-8"><style>{css_fonts}
*{{box-sizing:border-box}} body{{margin:0;background:#0e2130;color:#e6eef2;font-family:ui}}
#card{{width:2700px;grid-template-rows:auto auto auto auto;padding:44px 52px 34px;display:grid;grid-template-columns:{P.w}px 1fr;gap:20px 46px}}
h1{{grid-column:1/-1;margin:0;font-size:68px;font-weight:600;letter-spacing:-.01em}}
h1 span{{color:#8ea6b4;font-weight:400;font-size:40px;margin-left:18px}}
.map{{position:relative;border-radius:8px;overflow:hidden;height:{P.h}px}}
.inset{{position:absolute;left:22px;bottom:22px;border:2px solid #8ea6b4;border-radius:6px;overflow:hidden;background:#12283a}}
.inset .t{{position:absolute;top:6px;left:10px;font-size:26px;color:#e6eef2;text-shadow:0 0 4px #0e2130}}
svg{{display:block}} .sea{{fill:#12283a}} .nb{{fill:#264457;stroke:#12283a;stroke-width:1}}
.st{{stroke:#0e2130;stroke-width:.9;stroke-linejoin:round}}
.relief{{mix-blend-mode:soft-light;pointer-events:none}}
.lb{{font-family:ui;font-weight:600;font-size:27px;fill:#0e2130;text-anchor:middle;paint-order:stroke;stroke:#ffffffb0;stroke-width:5px}}
.lb.sm{{font-size:24px}}
.nat{{fill:none;stroke:#0e2130;stroke-width:3.2;stroke-linejoin:round}}
.ct{{fill:#fff;stroke:#0e2130;stroke-width:2.5}}
.ctl{{font-family:ui;font-weight:600;font-size:21px;fill:#fff;paint-order:stroke;stroke:#0e2130cc;stroke-width:4.5px;stroke-linejoin:round}}
.cn{{font-family:ui;font-size:28px;fill:#8ea6b4;text-anchor:middle;letter-spacing:.06em;text-transform:uppercase}}
.leg{{display:flex;flex-direction:column;justify-content:space-between;height:{P.h}px}}
.row{{display:grid;grid-template-columns:30px 1fr auto;gap:16px;align-items:center;padding:7px 0;border-bottom:1.5px solid #1e3a4c}}
.sw{{width:30px;height:30px;border-radius:4px}}
.nm b{{display:block;font-size:31px;font-weight:600;line-height:1.05}}
.nm small{{display:block;font-size:22px;color:#8ea6b4;margin-top:2px}}
.nm em{{display:block;font-style:normal;font-family:txt,s_deva,s_beng,ui;font-size:21px;color:#c8d6de;margin-top:3px}}
.smp{{font-size:46px;font-weight:600;color:#fff;white-space:nowrap;line-height:1.25}}
.notes{{grid-column:1/-1;display:grid;grid-template-columns:1fr 1fr;gap:30px;margin-top:4px}}
.note{{border-left:4px solid #f2c94c;padding:4px 16px}} .note b{{display:block;font-size:30px;color:#f2c94c}}
.note span{{font-family:txt,ui;font-size:23px;color:#c8d6de}}
.foot{{grid-column:1/-1;font-size:20px;color:#5d7787}}
</style><div id="card"><h1>Écritures des panneaux<span>Inde · Bangladesh · Sri Lanka</span></h1>
<div class="map">{main}<div class="inset"><span class="t">Sri Lanka</span>{inset}</div></div>
<div class="leg">{rows}</div>
<div class="notes">{notes}</div>
<div class="foot">Atlas TGM · d'après Plonk It (Inde, Sri Lanka), reformulé · fond : Natural Earth · Sri Lanka : districts hachurés = mixte tamoul/cinghalais</div></div>'''
open(f"{D}/scripts/card.html", "w", encoding="utf-8").write(html)
print("ok", P.w, P.h)
