"""Build de l'atlas GeoGuessr : scanne images/, crée les miniatures, écrit data.js.

Usage : double-clic sur build.cmd, ou `python build.py` (Pillow requis : pip install pillow)

Arborescence :
  images/BR Brazil/telephone/DDD.png              pays (les 2 premières lettres = code ISO)
  images/_multi/JP+TW/phone/Japan.png         plusieurs pays
  images/_clusters/cyrillic/language/alphabet.png cluster (pays définis dans config.json)
  images/_world/bollard/europe.png                mondial
  Un dossier type peut combiner plusieurs types : .../bollard+poteau/fichier.png
  Un sous-dossier optionnel dans un type regroupe des fiches : images/ID Indonesia/other/Kabupaten/Java.png
  Le nom du fichier devient le titre de la fiche.
"""
import hashlib
import shutil
import json
import re
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps

ROOT = Path(__file__).parent
IMAGES, THUMBS, FULL = ROOT / "images", ROOT / "thumbs", ROOT / "thumbs" / "full"
CACHE_FILE = THUMBS / "_cache.json"
EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}
THUMB_MAX_W, THUMB_MAX_H = 900, 1600   # ~2x la taille affichée, net sur écran haute densité
LOWRES_PX = 1200                       # en dessous (plus grand côté), la fiche est signalée
LIGHT_SHARE = 0.45                     # part de pixels clairs au-delà de laquelle l'image est « sur fond blanc »
INK_COLOUR_MAX = 0.20                  # on n'inverse que si le dessin est quasi monochrome (sinon couleurs massacrées)
ANALYSE_V = 2                          # incrémenter pour forcer la ré-analyse de toutes les fiches

config = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
type_keys = {t["key"] for t in config["types"]}
clusters = config.get("clusters", {})
cache = json.loads(CACHE_FILE.read_text(encoding="utf-8")) if CACHE_FILE.exists() else {}

cards, problems, warnings, used_thumbs, used_full = [], [], [], set(), set()

# Trainers : apps.json validé puis injecté dans data.js (la page tourne en file://, pas de fetch possible)
APP_STATUSES = {"live", "wip", "local", "idea"}
APP_SHOWN = {"live", "wip"}                     # local/idea : pas d'URL en ligne, non affichés
known_iso = {d.name[:2] for d in IMAGES.iterdir() if d.is_dir() and not d.name.startswith("_")} if IMAGES.exists() else set()
apps = json.loads((ROOT / "apps.json").read_text(encoding="utf-8"))["apps"] if (ROOT / "apps.json").exists() else []
seen_ids = set()
for a in apps:
    where = f"apps.json [{a.get('id', '?')}]"
    for k in ("id", "name", "repo", "url", "status", "scope", "countries", "types"):
        if k not in a:
            problems.append(f"{where} : champ « {k} » manquant")
    if a.get("id") in seen_ids:
        problems.append(f"{where} : id en double")
    seen_ids.add(a.get("id"))
    if a.get("status") not in APP_STATUSES:
        problems.append(f"{where} : statut « {a.get('status')} » inconnu, valides : {', '.join(sorted(APP_STATUSES))}")
    bad_t = [t for t in a.get("types", []) if t not in type_keys]
    if bad_t:
        problems.append(f"{where} : type inconnu {bad_t}")
    bad_c = [c for c in a.get("countries", []) if c not in known_iso]
    if bad_c and known_iso:
        warnings.append(f"{where} : pays hors liste de l'Atlas (ignorés sur la carte) {bad_c}")
shown_apps = [a for a in apps if a.get("status") in APP_SHOWN]


def analyse(src, dst):
    """Crée la miniature WebP et mesure la part de fond clair."""
    with Image.open(src) as im:
        im = ImageOps.exif_transpose(im)
        size = im.size
        rgba = im.convert("RGBA")
        flat = Image.new("RGB", rgba.size, (255, 255, 255))
        flat.paste(rgba, mask=rgba.split()[3])
        sm = flat.resize((300, max(1, round(300 * size[1] / size[0]))))
        L = np.asarray(sm.convert("L"))
        hsv = np.asarray(sm.convert("HSV"), dtype=np.float32) / 255
        ink = L < 226
        light = 1 - ink.mean()
        colour = ((hsv[..., 1] > .3) & (hsv[..., 2] > .2) & ink).sum() / max(ink.sum(), 1)
        thumb = flat.copy()
        thumb.thumbnail((THUMB_MAX_W, THUMB_MAX_H), Image.LANCZOS)
        dst.parent.mkdir(parents=True, exist_ok=True)
        thumb.save(dst, "WEBP", quality=88, method=5)
    # Inversion en mode sombre : seulement les schémas clairs et monochromes (plaques, drapeaux, cartes colorées : jamais)
    return {"w": size[0], "h": size[1], "v": ANALYSE_V, "light": bool(light >= LIGHT_SHARE),
            "invert": bool(light >= LIGHT_SHARE and colour < INK_COLOUR_MAX)}


def make_full(src, dst):
    """Original en WebP haute qualité ; garde l'original tel quel s'il est déjà plus léger."""
    with Image.open(src) as im:
        im = ImageOps.exif_transpose(im)
        if max(im.size) > 16000:
            im.thumbnail((16000, 16000), Image.LANCZOS)
        im = im.convert("RGBA" if im.mode in ("RGBA", "LA", "P") and "transparency" in im.info or im.mode in ("RGBA", "LA") else "RGB")
        im.save(dst, "WEBP", quality=90, method=4)
    if dst.stat().st_size > src.stat().st_size and src.suffix.lower() == ".webp":
        shutil.copy2(src, dst)


def resolve_scope(parts):
    """Retourne (countries, cluster, world, reste_du_chemin) ou lève ValueError."""
    top = parts[0]
    if top == "_world":
        return [], None, True, parts[1:]
    if top == "_clusters":
        if len(parts) < 2 or parts[1] not in clusters:
            raise ValueError(f"cluster « {parts[1] if len(parts) > 1 else '?'} » absent de config.json")
        return clusters[parts[1]]["countries"], parts[1], False, parts[2:]
    if top == "_multi":
        if len(parts) < 2:
            raise ValueError("une fiche multi-pays doit être dans _multi/<ISO+ISO>/<type>/")
        codes = [c.strip().upper() for c in parts[1].split("+")]
        if not all(re.fullmatch(r"[A-Z]{2}", c) for c in codes):
            raise ValueError(f"« {parts[1]} » doit être de la forme JP+TW")
        return codes, None, False, parts[2:]
    m = re.match(r"([A-Za-z]{2})(\s|$)", top)
    if not m:
        raise ValueError(f"le dossier « {top} » doit commencer par un code ISO (ex. « BR Brazil »)")
    return [m.group(1).upper()], None, False, parts[1:]


# Fiches « (local) » : contenus tiers (Plonk It…) pour usage perso, jamais publiés.
# build.py --public les ignore (utilisé par publish.ps1) ; build.cmd les inclut.
PUBLIC = "--public" in sys.argv
LOCAL_TAG = "(local)"

# En local, une fiche « X (local) » remplace sa version publique « X » (même dossier) : pas de doublon
_all = [f for f in IMAGES.rglob("*") if f.is_file() and f.suffix.lower() in EXTS]
HAS_LOCAL = {(f.parent, re.sub(r"\s*\(local\)", "", f.stem, flags=re.I).strip().lower()) for f in _all if LOCAL_TAG in f.stem.lower()}

for f in sorted(_all):
    is_local = LOCAL_TAG in f.stem.lower()
    if PUBLIC and is_local:
        continue
    if not PUBLIC and not is_local and (f.parent, f.stem.strip().lower()) in HAS_LOCAL:
        continue
    rel = f.relative_to(IMAGES)
    try:
        countries, cluster, world, rest = resolve_scope(rel.parts)
    except ValueError as e:
        problems.append(f"{rel} : {e}")
        continue
    if len(rest) not in (2, 3):
        problems.append(f"{rel} : type manquant (ex. …/bollard/fichier.png) ou trop de sous-dossiers (un seul niveau de groupe : …/other/Kabupaten/fichier.png) ; relance setup-atlas.ps1 pour migrer d'anciens noms")
        continue
    group = rest[1].strip() if len(rest) == 3 else ""
    types = [t for t in rest[0].lower().split("+") if t]
    unknown = [t for t in types if t not in type_keys]
    if unknown:
        problems.append(f"{rel} : type inconnu {unknown}, types valides : {', '.join(sorted(type_keys))}")
        continue

    key = rel.as_posix()
    mtime = f.stat().st_mtime
    # le nom change quand l'image change : le navigateur ne ressert jamais une ancienne version en cache
    stem = hashlib.sha1(f"{key}|{mtime}".encode("utf-8")).hexdigest()[:16]
    thumb_name = stem + ".webp"
    thumb = THUMBS / thumb_name
    info = cache.get(key)
    if not info or info.get("mtime") != mtime or info.get("v") != ANALYSE_V or not thumb.exists():
        info = analyse(f, thumb) | {"mtime": mtime}
        cache[key] = info
    used_thumbs.add(thumb_name)
    # version pleine résolution en WebP (souvent 5 à 10x plus léger qu'un PNG), nom ASCII
    full_name = stem + ".webp"
    full = FULL / full_name
    if not full.exists():
        FULL.mkdir(parents=True, exist_ok=True)
        make_full(f, full)
    used_full.add(full_name)

    cards.append({
        "id": key,
        "file": "thumbs/full/" + full_name,
        "thumb": "thumbs/" + thumb_name,
        "countries": countries,
        "cluster": cluster,
        "world": world,
        "types": types,
        "group": group,
        "title": re.sub(r"\s*\(local\)", "", f.stem, flags=re.I).replace("_", " ").strip(),
        "local": is_local,
        "w": info["w"],
        "h": info["h"],
        "invert": info["invert"],
        "light": info.get("light", False),
        "lowres": max(info["w"], info["h"]) < LOWRES_PX,
    })

# Ménage : miniatures et entrées de cache orphelines
THUMBS.mkdir(exist_ok=True)
for t in THUMBS.glob("*.webp"):
    if t.name not in used_thumbs:
        t.unlink()
for t in FULL.glob("*") if FULL.exists() else []:
    if t.name not in used_full:
        t.unlink()
cache = {k: v for k, v in cache.items() if k in {c["id"] for c in cards}}
CACHE_FILE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")

data = {"types": config["types"], "clusters": clusters, "cards": cards, "apps": shown_apps}
(ROOT / "data.js").write_text(
    "// Généré par build.py, ne pas modifier à la main\nwindow.ATLAS = "
    + json.dumps(data, ensure_ascii=False) + ";\n",
    encoding="utf-8",
)

low = [c["id"] for c in cards if c["lowres"]]
print(f"{len(cards)} fiche(s) indexée(s), {len(shown_apps)} trainer(s).")
if low:
    print(f"\n{len(low)} fiche(s) en basse résolution (< {LOWRES_PX} px), à remplacer si tu trouves mieux :")
    for x in low:
        print("  -", x)
if warnings:
    print(f"\n{len(warnings)} avertissement(s) :")
    for w in warnings:
        print("  -", w)
if problems:
    print(f"\n{len(problems)} fichier(s) ignoré(s) :")
    for p in problems:
        print("  -", p)
    sys.exit(1)
