"""Fiches « Écritures » par groupe, sur le modèle de south_asia.py :
carte colorée par langue (pays entiers, hachures = deux écritures), légende avec
repères et exemple dans sa police, notes de contraste.
Usage : python script_groups.py [cyrillic slavic nordic sea]  → ../scripts/<clé>.html et .png
Dépendances (dossier parent, voir README) : ne50_admin0.geojson, bm/shadedrelief.jpg,
fonts/ (barlow, barlow-condensed, noto-sans, noto-sans-thai, noto-sans-lao, noto-sans-khmer)."""
import base64, io, json, math, os, sys
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from script_groups_data import CARDS

D = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
Image.MAX_IMAGE_PIXELS = None
A0 = json.load(open(f"{D}/ne50_admin0.geojson", encoding="utf-8"))
def iso_of(f):
    p = f["properties"]
    return p.get("ISO_A2_EH") if p.get("ISO_A2_EH") not in (None, "-99") else p.get("ISO_A2")

class Proj:
    """Équirectangulaire corrigée en cos(latitude moyenne)."""
    def __init__(s, lon0, lon1, lat0, lat1, w):
        s.K = math.cos(math.radians((lat0 + lat1) / 2))
        s.lon0, s.lat1 = lon0, lat1; s.k = w / ((lon1 - lon0) * s.K)
        s.w, s.h = w, round((lat1 - lat0) * s.k); s.box = (lon0, lon1, lat0, lat1)
    def __call__(s, lon, lat): return ((lon - s.lon0) * s.K * s.k, (s.lat1 - lat) * s.k)

_rgb = None
def relief(P, gain=380):
    global _rgb
    if _rgb is None: _rgb = Image.open(f"{D}/bm/shadedrelief.jpg")
    SW, SH = _rgb.size; lon0, lon1, lat0, lat1 = P.box
    a = np.asarray(_rgb.crop((int((lon0 + 180) / 360 * SW), int((90 - lat1) / 180 * SH),
                              int((lon1 + 180) / 360 * SW), int((90 - lat0) / 180 * SH))), dtype=np.int16)
    land = ~((a[..., 2] > a[..., 0] + 18) & (a[..., 2] > a[..., 1]))
    L = a.mean(-1).astype(np.float32) + 1; m = land.astype(np.float32)
    B = gaussian_filter(L * m, 10) / np.maximum(gaussian_filter(m, 10), 1e-3)
    g = np.clip(128 + (np.where(land, L / np.maximum(B, 1), 1.0) - 1) * gain, 0, 255).astype(np.uint8)
    buf = io.BytesIO(); Image.fromarray(g, "L").resize((P.w, P.h), Image.LANCZOS).save(buf, "PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()

def rings(g):
    return g["coordinates"] if g["type"] == "Polygon" else [r for p in g["coordinates"] for r in p]
def path(g, P, simplify=0.5):
    out = []
    lon0, lon1, lat0, lat1 = P.box
    for r in rings(g):
        if all(lon < lon0 - 5 or lon > lon1 + 5 for lon, _ in r[::7]): continue
        pts, last = [], None
        for lon, lat in r:
            x, y = P(lon, lat)
            if last and abs(x - last[0]) + abs(y - last[1]) < simplify: continue
            pts.append(f"{x:.1f},{y:.1f}"); last = (x, y)
        if len(pts) > 2: out.append("M" + "L".join(pts) + "Z")
    return "".join(out)

FONTS = {  # famille : [(dossier fontsource, fichier sans -<poids>-normal.woff2)]
  "ui": [("barlow-condensed", "barlow-condensed-latin"), ("barlow-condensed", "barlow-condensed-latin-ext")],
  "txt": [("barlow", "barlow-latin"), ("barlow", "barlow-latin-ext")],
  "s_lat": [("noto-sans", "noto-sans-latin")], "s_latx": [("noto-sans", "noto-sans-latin-ext")],
  "s_cyr": [("noto-sans", "noto-sans-cyrillic")], "s_cyrx": [("noto-sans", "noto-sans-cyrillic-ext")],
  "s_thai": [("noto-sans-thai", "noto-sans-thai-thai")], "s_lao": [("noto-sans-lao", "noto-sans-lao-lao")],
  "s_khmer": [("noto-sans-khmer", "noto-sans-khmer-khmer")],
}
SAMPLE_STACK = "s_lat,s_latx,s_cyr,s_cyrx,s_thai,s_lao,s_khmer"
def font_css():
    css = []
    for fam, files in FONTS.items():
        for pkg, base in files:
            for w in (400, 600):
                f = f"{D}/fonts/{pkg}/files/{base}-{w}-normal.woff2"
                if not os.path.exists(f): raise SystemExit(f"police manquante : {f}")
                b = base64.b64encode(open(f, "rb").read()).decode()
                css.append(f"@font-face{{font-family:{fam};font-weight:{w};src:url(data:font/woff2;base64,{b})}}")
    return "".join(css)

def map_svg(C, P, focus, labels, countries, cities, sid):
    col = {k: c for k, _, c, *_ in C["langs"]}
    defs, s = [], [f'<rect width="100%" height="100%" class="sea"/>']
    for f in A0["features"]:
        if iso_of(f) not in focus:
            d = path(f["geometry"], P)
            if d: s.append(f'<path class="nb" d="{d}"/>')
    for f in A0["features"]:
        iso = iso_of(f)
        if iso not in focus: continue
        k = C["fill"][iso]
        if isinstance(k, tuple):
            a, b = col.get(k[0], k[0]), col.get(k[1], k[1])
            pid = f"h{sid}{iso}"
            defs.append(f'<pattern id="{pid}" width="16" height="16" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
                        f'<rect width="16" height="16" fill="{b}"/><rect width="9" height="16" fill="{a}"/></pattern>')
            fill = f"url(#{pid})"
        else: fill = col[k]
        s.append(f'<path class="st" fill="{fill}" d="{path(f["geometry"], P, 0.3)}"/>')
    s.append(f'<image href="{relief(P)}" width="{P.w}" height="{P.h}" class="relief"/>')
    for lon, lat, t in countries:
        x, y = P(lon, lat); s.append(f'<text class="cn" x="{x:.0f}" y="{y:.0f}">{t}</text>')
    for lon, lat, n, side in cities:
        x, y = P(lon, lat); dx = 11 if side == "r" else -11
        s.append(f'<circle class="ct" cx="{x:.0f}" cy="{y:.0f}" r="5"/><text class="ctl" x="{x+dx:.0f}" y="{y+7:.0f}" '
                 f'text-anchor="{"start" if side == "r" else "end"}">{n}</text>')
    for lon, lat, t in labels:
        x, y = P(lon, lat); s.append(f'<text class="lb" x="{x:.0f}" y="{y:.0f}">{t}</text>')
    return (f'<svg width="{P.w}" height="{P.h}" viewBox="0 0 {P.w} {P.h}"><defs>{"".join(defs)}</defs>'
            + "\n".join(s) + "</svg>")

def build(key):
    C = CARDS[key]
    focus = set(C["fill"])
    P = Proj(*C["main"])
    main = map_svg(C, P, focus, C["labels"], C["countries"], C["cities"], "m")
    inset = ""
    if C.get("inset"):
        I = C["inset"]; IP = Proj(*I["box"])
        pos = {"tl": "left:22px;top:22px", "bl": "left:22px;bottom:22px", "tr": "right:22px;top:22px"}[I.get("where", "bl")]
        inset = (f'<div class="inset" style="{pos}"><span class="t">{I["title"]}</span>'
                 + map_svg(C, IP, focus, I["labels"], I["countries"], I["cities"], "i") + "</div>")
    extra = C.get("extra", {})
    rows = "".join(f'''<div class="row"><span class="sw" style="background:{c}"></span>
<div class="nm"><b>{lbl}</b><small>{where}</small><em>{cue}</em></div>
<div class="smp"><span>{smp}</span>{f"<i>{extra[k]}</i>" if k in extra else ""}</div></div>'''
                   for k, lbl, c, smp, where, cue in C["langs"])
    notes = "".join(f'<div class="note"><b>{t}</b><span>{x}</span></div>' for t, x in C["notes"])
    side = C.get("notes_side")
    side_notes = f'<div class="notes side">{notes}</div>' if side else ""
    cmp = C.get("compare")
    if cmp:
        col = {k: c for k, _, c, *_ in C["langs"]}
        head = "".join(f'<th style="color:{col[k]}">{lab}</th>' for k, lab in cmp["cols"])
        body = "".join(f'<tr><td class="snd">{snd}</td>' + "".join(f"<td>{g}</td>" if g != "—" else '<td class="no">—</td>' for g in gl) + "</tr>"
                       for snd, gl in cmp["rows"])
        side_notes = (f'<style>.cmp td{{{{font-size:{cmp.get("fs", 76)}px}}}}</style><div class="cmp"><b>{cmp["title"]}</b><table><tr><th></th>{head}</tr>{body}</table></div>'
                      + side_notes)
    bottom_notes = "" if side else f'<div class="notes">{notes}</div>'
    foot = "Atlas TGM · repères reformulés (Wikipedia, Plonk It) · fond : Natural Earth" + (f" · {C['foot']}" if C.get("foot") else "")
    html = f'''<!doctype html><meta charset="utf-8"><style>{font_css()}
*{{box-sizing:border-box}} body{{margin:0;background:#0e2130;color:#e6eef2;font-family:ui}}
#card{{width:2700px;padding:44px 52px 34px;display:grid;grid-template-columns:{P.w}px 1fr;gap:20px 46px}}
h1{{grid-column:1/-1;margin:0;font-size:68px;font-weight:600;letter-spacing:-.01em}}
h1 span{{color:#8ea6b4;font-weight:400;font-size:40px;margin-left:18px;font-family:ui,{SAMPLE_STACK}}}
.map{{position:relative;border-radius:8px;overflow:hidden;height:{P.h}px}}
.inset{{position:absolute;border:2px solid #8ea6b4;border-radius:6px;overflow:hidden;background:#12283a}}
.inset .t{{position:absolute;top:6px;left:10px;font-size:28px;color:#e6eef2;text-shadow:0 0 4px #0e2130;z-index:1}}
svg{{display:block}} .sea{{fill:#12283a}} .nb{{fill:#264457;stroke:#12283a;stroke-width:1}}
.st{{stroke:#0e2130;stroke-width:1.6;stroke-linejoin:round}}
.relief{{mix-blend-mode:soft-light;pointer-events:none}}
.lb{{font-family:ui;font-weight:600;font-size:30px;fill:#0e2130;text-anchor:middle;paint-order:stroke;stroke:#ffffffb8;stroke-width:6px}}
.ct{{fill:#fff;stroke:#0e2130;stroke-width:2.5}}
.ctl{{font-family:ui,{SAMPLE_STACK};font-weight:600;font-size:21px;fill:#fff;paint-order:stroke;stroke:#0e2130cc;stroke-width:4.5px;stroke-linejoin:round}}
.cn{{font-family:ui;font-size:26px;fill:#8ea6b4;text-anchor:middle;letter-spacing:.06em;text-transform:uppercase}}
.leg{{display:flex;flex-direction:column;justify-content:flex-start;gap:4px}}
.row{{display:grid;grid-template-columns:30px 1fr auto;gap:18px;align-items:center;padding:12px 0;border-bottom:1.5px solid #1e3a4c}}
.sw{{width:30px;height:30px;border-radius:4px}}
.nm b{{display:block;font-size:34px;font-weight:600;line-height:1.05}}
.nm small{{display:block;font-size:23px;color:#8ea6b4;margin-top:3px}}
.nm em{{display:block;font-style:normal;font-family:txt,{SAMPLE_STACK};font-size:24px;color:#c8d6de;margin-top:4px}}
.smp{{text-align:right;font-family:{SAMPLE_STACK};color:#fff;line-height:1.25}}
.smp span{{display:block;font-size:50px;font-weight:600;white-space:nowrap}}
.smp i{{display:block;font-style:normal;font-size:28px;color:#c8d6de;white-space:nowrap}}
.notes{{grid-column:1/-1;display:grid;grid-template-columns:repeat({len(C["notes"])},1fr);gap:30px;margin-top:4px}}
.cmp{{margin-top:22px}} .cmp b{{display:block;font-size:30px;color:#f2c94c;margin-bottom:6px}}
.cmp table{{border-collapse:collapse;width:100%}} .cmp th{{font-size:30px;font-weight:600;text-align:center;padding:4px}}
.cmp td{{font-family:{SAMPLE_STACK};font-size:76px;text-align:center;color:#fff;padding:2px 0;border-top:1.5px solid #1e3a4c;line-height:1.3}}
.cmp td.no{{color:#3d5a6c}} .cmp td.snd{{font-family:ui;font-size:30px;color:#8ea6b4;text-align:left;width:120px}}
.notes.side{{grid-column:auto;grid-template-columns:1fr;gap:22px;margin-top:26px}}
.note{{border-left:4px solid #f2c94c;padding:4px 16px}} .note b{{display:block;font-size:30px;color:#f2c94c}}
.note span{{font-family:txt,{SAMPLE_STACK};font-size:24px;color:#c8d6de}}
.foot{{grid-column:1/-1;font-size:20px;color:#5d7787}}
</style><div id="card"><h1>{C["title"]}<span>{C["sub"]}</span></h1>
<div class="map">{main}{inset}</div>
<div class="leg">{rows}{side_notes}</div>
{bottom_notes}
<div class="foot">{foot}</div></div>'''
    os.makedirs(f"{D}/scripts", exist_ok=True)
    hp = f"{D}/scripts/{key}.html"
    open(hp, "w", encoding="utf-8").write(html)
    return hp, C["out"]

def render(hp, png):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page(viewport={"width": 2700, "height": 1000})
        pg.goto("file://" + os.path.abspath(hp)); pg.wait_for_timeout(1500)
        pg.locator("#card").screenshot(path=png); b.close()

if __name__ == "__main__":
    for key in sys.argv[1:] or list(CARDS):
        hp, out = build(key)
        png = hp[:-5] + ".png"
        render(hp, png)
        print(key, "→", png, "| à ranger dans images/" + out)
