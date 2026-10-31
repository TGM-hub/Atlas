"""Hors-ligne et installation (PWA) pour l'Atlas et les trainers : écrit, dans chaque repo,
sw.js, manifest.webmanifest, icons/icon-192.png et icon-512.png, et le bloc <!-- tgm-pwa --> des pages.

    python tools/pwa.py              # tous les repos
    python tools/pwa.py city-placer  # un seul

Relançable sans risque : le bloc des pages est remplacé, pas dupliqué ; les icônes existantes sont gardées
(supprimer icons/ pour les refaire, Pillow requis).

Service worker (GitHub Pages, jamais en file://) :
  - pages, scripts, données : réseau d'abord (4 s), cache si hors ligne ; toujours la dernière version en ligne ;
  - images et sons : cache d'abord (gardés au fil des visites, jamais tout d'un coup) ;
  - au premier passage : les fichiers de base de la page (et les miniatures pour l'Atlas) ;
  - rien hors du repo (fonds de carte, polices Google, drapeaux) n'est mis en cache.
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from smoke import APPS, repo_dir  # noqa: E402  (même liste de repos que les tests)

NAVY, SIGN = "#12283a", "#f2c94c"
INFO = {   # name, short name, letters on the icon, pages carrying the block
    "Atlas": ("GeoGuessr Atlas", "Atlas", "A", ["index.html", "daily.html", "confusions.html"]),
    "phone-codes": ("Phone codes", "Phone codes", "☎", ["index.html"]),
    "plate-trainer": ("Plate Trainer", "Plates", "PL", ["index.html"]),
    "bollards-trainer": ("Bollard Trainer", "Bollards", "BO", ["index.html"]),
    "city-placer": ("City Placer", "City Placer", "CP", ["index.html"]),
    "script-identifier-geoguessr": ("Sign Reader", "Sign Reader", "SR", ["index.html"]),
    "vietnam-province-guesser": ("Vietnam provinces", "Vietnam", "VN", ["index.html"]),
    "indonesia-kabupaten": ("Indonesia kabupaten", "Kabupaten", "KB", ["index.html", "src/template.html"]),
    "russian-pannels-learning": ("Cyrillic Reader", "Cyrillic", "КИ", ["index.html"]),
}
SW = r"""// Généré par Atlas/tools/pwa.py, ne pas modifier à la main.
const CACHE = 'tgm-__REPO__-v1';
const SHELL = __SHELL__;
const THUMBS = __THUMBS__;   // Atlas : miniatures listées dans data.js, gardées dès la première visite
const MEDIA = /\.(png|jpe?g|webp|gif|svg|mp3)$/i;

self.addEventListener('install', e => e.waitUntil((async () => {
  const c = await caches.open(CACHE);
  await c.addAll(SHELL);
  if (THUMBS) {
    try {
      const t = await (await fetch('data.js', { cache: 'no-cache' })).text();
      await c.addAll([...new Set(t.match(/thumbs\/[0-9a-f]+\.webp/g) || [])]);
    } catch (err) {}
  }
  await self.skipWaiting();
})()));
self.addEventListener('activate', e => e.waitUntil((async () => {
  for (const k of await caches.keys()) if (k.startsWith('tgm-__REPO__-') && k !== CACHE) await caches.delete(k);
  await self.clients.claim();
})()));
const keep = (req, res) => { if (res && res.ok && res.type === 'basic') { const copy = res.clone(); caches.open(CACHE).then(c => c.put(req, copy)); } return res; };
const timeout = (p, ms) => Promise.race([p, new Promise((_, no) => setTimeout(() => no(new Error('timeout')), ms))]);
self.addEventListener('fetch', e => {
  const req = e.request, url = new URL(req.url);
  if (req.method !== 'GET' || url.origin !== location.origin || !req.url.startsWith(self.registration.scope)) return;
  if (MEDIA.test(url.pathname)) {
    e.respondWith(caches.match(req).then(hit => hit || fetch(req).then(res => keep(req, res))));
    return;
  }
  e.respondWith(timeout(fetch(req), 4000).then(res => keep(req, res))
    .catch(() => caches.match(req, { ignoreSearch: true }).then(hit => hit || Response.error())));
});
"""
BLOCK = """<!-- tgm-pwa : hors-ligne et installation, généré par Atlas/tools/pwa.py -->
<link rel="manifest" href="manifest.webmanifest"><meta name="theme-color" content="#12283a">__ICON__
<script>if ('serviceWorker' in navigator && location.protocol.startsWith('http')) addEventListener('load', () => navigator.serviceWorker.register('sw.js').catch(() => {}));</script>
<!-- /tgm-pwa -->
"""


def shell_of(root, pages):
    files = {"./"}
    for p in pages:
        if p.startswith("src/"):
            continue
        files.add(p)
        txt = (root / p).read_text(encoding="utf-8")
        for ref in re.findall(r'<(?:script|link)\b[^>]*?\b(?:src|href)="([^"#?]+)"', txt):
            if not re.match(r"^(https?:|data:|//)", ref) and (root / ref).is_file() and not ref.endswith(".webmanifest"):
                files.add(ref)
    return sorted(files)


def icon(root, letters):
    out = root / "icons"
    if (out / "icon-512.png").exists() and (out / "icon-192.png").exists():
        return
    from PIL import Image, ImageDraw, ImageFont
    fonts = ["C:/Windows/Fonts/segoeuib.ttf", "C:/Windows/Fonts/arialbd.ttf", "C:/Windows/Fonts/seguisym.ttf",
             "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]
    out.mkdir(exist_ok=True)
    for size in (512, 192):
        im = Image.new("RGB", (size, size), NAVY)          # full square: also fine as a maskable icon
        d = ImageDraw.Draw(im)
        fs = int(size * (0.42 if len(letters) <= 1 else 0.32))
        font = next((ImageFont.truetype(f, fs) for f in fonts if Path(f).exists()), ImageFont.load_default())
        d.text((size / 2, size / 2), letters, fill=SIGN, font=font, anchor="mm")
        d.rounded_rectangle([size * .1, size * .1, size * .9, size * .9], radius=size * .12, outline=SIGN, width=max(2, size // 48))
        im.save(out / f"icon-{size}.png", optimize=True)


def apply(name):
    root = repo_dir(name)
    full, short, letters, pages = INFO[name]
    icon(root, letters)
    manifest = {"name": full, "short_name": short, "start_url": "./", "scope": "./", "display": "standalone",
                "background_color": NAVY, "theme_color": NAVY,
                "icons": [{"src": f"icons/icon-{s}.png", "sizes": f"{s}x{s}", "type": "image/png", "purpose": "any maskable"} for s in (192, 512)]}
    (root / "manifest.webmanifest").write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    for p in pages:
        f = root / p
        raw = f.read_bytes().decode("utf-8")
        eol = "\r\n" if "\r\n" in raw else "\n"
        s = re.sub(r"<!-- tgm-pwa .*?<!-- /tgm-pwa -->\n?", "", raw.replace("\r\n", "\n"), flags=re.S)
        has_icon = re.search(r'<link rel="(?:shortcut )?icon"', s)
        block = BLOCK.replace("__ICON__", "" if has_icon else '<link rel="icon" href="icons/icon-192.png">') \
                     .replace("<link rel=\"manifest\"", "<link rel=\"apple-touch-icon\" href=\"icons/icon-192.png\"><link rel=\"manifest\"")
        i = s.index("</head>")
        s = s[:i] + block + s[i:]
        f.write_bytes(s.replace("\n", eol).encode("utf-8"))
    shell = shell_of(root, pages) + ["manifest.webmanifest", "icons/icon-192.png"]
    sw = SW.replace("__REPO__", name.lower()).replace("__SHELL__", json.dumps(sorted(set(shell))))\
           .replace("__THUMBS__", "true" if name == "Atlas" else "false")
    (root / "sw.js").write_text(sw, encoding="utf-8", newline="\n")
    print(f"{name}: sw.js ({len(set(shell))} fichiers de base), manifest, icônes, {len(pages)} page(s)")


if __name__ == "__main__":
    names = [a for a in sys.argv[1:]] or list(INFO)
    for n in names:
        if not repo_dir(n).exists():
            print(f"{n} : dossier absent, ignoré"); continue
        apply(n)
