"""Briques communes des fiches Atlas : projection, relief, géométries Natural Earth, polices, rendu PNG."""
import base64, io, json, math, os
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter
from shapely.geometry import shape
from shapely.ops import polylabel, unary_union

D = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
Image.MAX_IMAGE_PIXELS = None
_rgb = None
A0 = json.load(open(f"{D}/ne50_admin0.geojson"))
A1 = json.load(open(f"{D}/ne10_admin1.geojson"))

class Proj:
    """Équirectangulaire corrigée en cos(latitude moyenne) : fidèle à l'échelle d'un pays."""
    def __init__(s, lon0, lon1, lat0, lat1, w):
        s.K = math.cos(math.radians((lat0 + lat1) / 2))
        s.lon0, s.lat1 = lon0, lat1; s.k = w / ((lon1 - lon0) * s.K)
        s.w, s.h = w, round((lat1 - lat0) * s.k); s.box = (lon0, lon1, lat0, lat1)
    def __call__(s, lon, lat): return ((lon - s.lon0) * s.K * s.k, (s.lat1 - lat) * s.k)
    def inv(s, x, y): return (s.lon0 + x / (s.K * s.k), s.lat1 - y / s.k)

def relief(P, gain=380):
    """Ombrage Natural Earth (domaine public) recadré sur la carte, en PNG data-URI."""
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
    for r in rings(g):
        pts, last = [], None
        for lon, lat in r:
            x, y = P(lon, lat)
            if last and abs(x - last[0]) + abs(y - last[1]) < simplify: continue
            pts.append(f"{x:.1f},{y:.1f}"); last = (x, y)
        if len(pts) > 2: out.append("M" + "L".join(pts) + "Z")
    return "".join(out)

def admin0(iso): return [f for f in A0["features"] if f["properties"]["ISO_A2_EH"] == iso]
def admin1(iso): return [f for f in A1["features"] if f["properties"]["iso_a2"] == iso]

def label_point(geom, P):
    """Point d'étiquette dans le plus grand morceau (pôle d'inaccessibilité), en pixels + surface en px²."""
    from shapely.geometry import Polygon
    g = shape(geom)
    parts = list(g.geoms) if g.geom_type == "MultiPolygon" else [g]
    big = max(parts, key=lambda p: p.area)
    pp = Polygon([P(x, y) for x, y in big.exterior.coords])
    pt = polylabel(pp.buffer(0), tolerance=0.5)
    return pt.x, pt.y, pp.area

def neighbours(P, focus, cls="nb"):
    return "\n".join(f'<path class="{cls}" d="{path(f["geometry"], P)}"/>' for f in A0["features"]
                     if f["properties"]["ISO_A2_EH"] not in focus)

FONT_FILES = {"ui": [("barlow-condensed-latin", 400), ("barlow-condensed-latin", 600), ("barlow-condensed-latin-ext", 400), ("barlow-condensed-latin-ext", 600)],
              "txt": [("barlow-latin", 400), ("barlow-latin-ext", 400), ("barlow-latin", 600), ("barlow-latin-ext", 600)]}
def fonts(extra=None):
    css = []
    for fam, files in {**FONT_FILES, **(extra or {})}.items():
        for base, w in files:
            for dp, _, fs in os.walk(f"{D}/fonts"):
                if f"{base}-{w}-normal.woff2" in fs:
                    b = base64.b64encode(open(os.path.join(dp, f"{base}-{w}-normal.woff2"), "rb").read()).decode()
                    css.append(f"@font-face{{font-family:{fam};font-weight:{w};src:url(data:font/woff2;base64,{b})}}")
    return "".join(css)

BASE_CSS = """*{box-sizing:border-box} body{margin:0;background:#0e2130;color:#e6eef2;font-family:ui}
svg{display:block} .sea{fill:#12283a} .nb{fill:#264457;stroke:#12283a;stroke-width:1}
.relief{mix-blend-mode:soft-light;pointer-events:none}
.cn{font-family:ui;font-size:30px;fill:#8ea6b4;text-anchor:middle;letter-spacing:.08em;text-transform:uppercase}
h1{margin:0;font-size:68px;font-weight:600;letter-spacing:-.01em} h1 span{color:#8ea6b4;font-weight:400;font-size:40px;margin-left:18px}
.foot{font-size:20px;color:#5d7787}"""

def render(html_path, png_path, width=2700):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page(viewport={"width": width, "height": 1000})
        pg.goto("file://" + os.path.abspath(html_path)); pg.wait_for_timeout(1200)
        pg.locator("#card").screenshot(path=png_path); b.close()
