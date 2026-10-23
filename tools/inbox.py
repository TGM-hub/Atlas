r"""Routine d'alimentation de l'Atlas : range les images déposées dans _inbox/.

Dépose une image dans _inbox\ avec un nom libre, puis lance inbox.cmd :
    « phone br Indicatifs DDD.png »          -> images\BR Brazil\phone\Indicatifs DDD.png
    « plaque pologne voïvodies.png »          -> images\PL Poland\plate\Voïvodies.png
    « language japon taiwan kana.png »        -> images\_multi\JP+TW\language\Kana.png
    « cyrillique language alphabet.png »      -> images\_clusters\cyrillic\language\Alphabet.png
    « monde bollard Europe.png »              -> images\_world\bollard\Europe.png
    « other id [Kabupaten] Java.png »         -> images\ID Indonesia\other\Kabupaten\Java.png
    « phone es Spain codes (local).png »      -> fiche locale, jamais publiée
Pays : nom français ou anglais, ou code ISO (en MAJUSCULES s'il ressemble à un mot : DE, ES, IT…).
Types et clusters : clés, libellés et alias de config.json (« plaque », « indicatif », « poteau »…).
Le reste du nom devient le titre, nettoyé (« final », « updated », « darkmode », « v5 »…).
Si le pays ou le type manque, le script pose la question ; sinon il ne demande rien.

Options : --dry-run (montre sans rien déplacer), --yes (ne pose aucune question, laisse les cas
douteux dans _inbox), --no-build (ne relance pas build.py à la fin).
"""
import json, re, subprocess, sys, unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INBOX, IMAGES = ROOT / "_inbox", ROOT / "images"
EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}
DRY, YES, NOBUILD = "--dry-run" in sys.argv, "--yes" in sys.argv, "--no-build" in sys.argv

# Mots retirés du titre (bruit de nom de fichier)
JUNK = {"final", "finale", "version", "hopefully", "updated", "update", "maj", "darkmode", "dark", "mode",
        "lightmode", "copy", "copie", "png", "jpg", "jpeg", "webp", "img", "image", "screenshot", "new", "nouveau"}
JUNK_RE = re.compile(r"^(v\d+|\d{3,4}x\d{3,4}|\(\d+\)|\d+)$", re.I)
# ISO en minuscules : jamais pour les mots-outils, et seulement en tête de nom (« phone id … ») pour
# les codes qui sont aussi des mots courants ; en MAJUSCULES, un code ISO est toujours pris
NEVER_ISO = {"de", "la", "le", "et", "en", "du", "un", "an", "at", "by", "do", "on", "or", "so", "to", "is", "as", "am"}
RISKY_ISO = {"es", "it", "in", "no", "be", "my", "me", "us", "ca", "id", "se", "pt", "pr", "ne", "ma", "mo",
             "pa", "pe", "re", "si", "sa", "na", "al", "ga", "gu", "tv"}
STOP = {"de", "la", "le", "les", "du", "des", "et", "of", "the", "and", "d", "l"}
WORLD = {"world", "monde", "mondial", "global", "worldwide"}
EXTRA = {"GB": ["uk", "angleterre", "england", "ecosse", "scotland", "royaume uni"], "US": ["usa", "etats unis", "america"],
         "AE": ["uae", "emirats"], "CZ": ["czechia", "tcheque"], "NL": ["hollande", "holland"], "KR": ["coree", "korea"],
         "RU": ["russia"], "ZA": ["rsa"]}


def norm(s):
    s = unicodedata.normalize("NFD", s)
    return "".join(c for c in s if not unicodedata.combining(c)).lower()


def load():
    config = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
    world = (ROOT / "map.js").read_text(encoding="utf-8")
    names = {k: json.loads(re.search(rf'"{k}":(\{{[^}}]*\}})', world).group(1)) for k in ("names", "namesEn")}
    folders = {d.name[:2].upper(): d.name for d in IMAGES.iterdir() if d.is_dir() and re.match(r"[A-Z]{2}\s", d.name)}
    # phrase normalisée (1 à 4 mots) -> valeur
    countries, types, clusters = {}, {}, {}
    for iso in set(names["names"]) | set(folders):
        for n in [names["names"].get(iso, ""), names["namesEn"].get(iso, ""), folders.get(iso, "")[3:], *EXTRA.get(iso, [])]:
            if n: countries[" ".join(re.findall(r"[a-z0-9]+", norm(n)))] = iso
    for t in config["types"]:
        for n in [t["key"], t["label"], *t.get("aliases", [])]:
            types[" ".join(re.findall(r"[a-z0-9]+", norm(n)))] = t["key"]
    for k, c in config.get("clusters", {}).items():
        for n in [k, c["label"], *c.get("aliases", [])]:
            clusters[" ".join(re.findall(r"[a-z0-9]+", norm(n)))] = k
    return config, names, folders, countries, types, clusters


def parse(stem, countries, types, clusters, folders):
    local = bool(re.search(r"\(local\)", stem, re.I))
    stem = re.sub(r"\(local\)", " ", stem, flags=re.I)
    group = None
    m = re.search(r"\[([^\]]+)\]", stem)
    if m:
        group, stem = m.group(1).strip(), stem[:m.start()] + " " + stem[m.end():]
    raw = re.findall(r"[^\W_]+|\(\d+\)", stem.replace("-", " ").replace("_", " "))
    low = [norm(w) for w in raw]
    used = [False] * len(raw)
    found = {"countries": [], "type": None, "cluster": None, "world": False}

    def take(i, n):
        for j in range(i, i + n): used[j] = True

    i = 0
    while i < len(raw):                      # plus longue phrase d'abord (« south korea », « road lines »)
        hit = False
        for n in (4, 3, 2, 1):
            if i + n > len(raw) or any(used[i:i + n]): continue
            ph = " ".join(low[i:i + n])
            if ph in countries and countries[ph] not in found["countries"]:
                found["countries"].append(countries[ph]); take(i, n); hit = True; break
            if ph in types and not found["type"]:
                found["type"] = types[ph]; take(i, n); hit = True; break
            if ph in clusters and not found["cluster"]:
                found["cluster"] = clusters[ph]; take(i, n); hit = True; break
            if n == 1 and ph in WORLD and not found["world"]:
                found["world"] = True; take(i, 1); hit = True; break
        i += n if hit else 1
    # codes ISO : en MAJUSCULES toujours, en minuscules seulement s'ils ne sont pas aussi des mots
    for i, w in enumerate(raw):
        if used[i] or len(w) != 2: continue
        iso = w.upper()
        if iso in found["countries"]:      # « phone es Spain » : le code double le nom
            used[i] = True; continue
        lw = w.lower()
        ok = w.isupper() or (lw not in NEVER_ISO and (lw not in RISKY_ISO or i <= 1))
        if iso in folders and ok:
            found["countries"].append(iso); used[i] = True
    title_words = [w for w, u in zip(raw, used) if not u and norm(w) not in JUNK and not JUNK_RE.match(w)]
    while title_words and norm(title_words[0]) in STOP: title_words.pop(0)       # « de la » orphelins
    while title_words and norm(title_words[-1]) in STOP: title_words.pop()
    title = " ".join(title_words).strip()
    if title: title = title[0].upper() + title[1:]
    return found, title, group, local


def ask(prompt, options):
    if YES or not sys.stdin.isatty(): return None
    print(prompt)
    for k, (label, _) in enumerate(options, 1): print(f"   {k}. {label}")
    a = input("   Numéro, ou Entrée pour laisser dans _inbox : ").strip()
    return options[int(a) - 1][1] if a.isdigit() and 1 <= int(a) <= len(options) else None


def ask_text(prompt, lookup):
    if YES or not sys.stdin.isatty(): return None
    a = norm(input(prompt).strip())
    return lookup.get(" ".join(re.findall(r"[a-z0-9]+", a))) or (a.upper() if len(a) == 2 else None)


def main():
    if not INBOX.exists():
        INBOX.mkdir(); print("Dossier _inbox créé : dépose-y les images, puis relance inbox.cmd."); return
    config, names, folders, countries, types, clusters = load()
    files = sorted(f for f in INBOX.iterdir() if f.is_file() and f.suffix.lower() in EXTS)
    if not files:
        print("_inbox est vide."); return
    moved, left = [], []
    type_opts = [(f"{t['label']} ({t['key']})", t["key"]) for t in config["types"]]
    for f in files:
        found, title, group, local = parse(f.stem, countries, types, clusters, folders)
        print(f"\n« {f.name} »")
        if not found["type"]:
            found["type"] = ask("   Type introuvable dans le nom :", type_opts)
        if found["type"] and not (found["countries"] or found["cluster"] or found["world"]):
            iso = ask_text("   Pays introuvable : tape un pays (nom ou ISO), « monde », ou Entrée pour passer : ",
                           {**countries, **{w: "WORLD" for w in WORLD}})
            if iso == "WORLD": found["world"] = True
            elif iso: found["countries"] = [iso]
        if not found["type"] or not (found["countries"] or found["cluster"] or found["world"]):
            print("   -> laissé dans _inbox (pays ou type manquant)"); left.append(f.name); continue
        unknown = [c for c in found["countries"] if c not in folders]
        if unknown:
            print(f"   -> laissé dans _inbox : {', '.join(unknown)} n'a pas de dossier dans images\\ (hors couverture ?)")
            left.append(f.name); continue
        if found["world"]: base = IMAGES / "_world"
        elif found["cluster"]: base = IMAGES / "_clusters" / found["cluster"]
        elif len(found["countries"]) > 1: base = IMAGES / "_multi" / "+".join(sorted(found["countries"]))
        else: base = IMAGES / folders[found["countries"][0]]
        dest_dir = base / found["type"] / (group or "")
        if not title:   # rien d'autre dans le nom : titre = type, plus le pays
            title = next(t["label"] for t in config["types"] if t["key"] == found["type"])
        name = title + (" (local)" if local else "")
        dest = dest_dir / (name + f.suffix.lower())
        k = 2
        while dest.exists(): dest, k = dest_dir / f"{name} {k}{f.suffix.lower()}", k + 1
        print(f"   -> {dest.relative_to(ROOT)}")
        if not DRY:
            dest_dir.mkdir(parents=True, exist_ok=True)
            f.rename(dest)
        moved.append(dest)
    print(f"\n{len(moved)} fiche(s) rangée(s), {len(left)} laissée(s) dans _inbox." + (" (simulation)" if DRY else ""))
    if moved and not DRY and not NOBUILD:
        print("Build de l'Atlas…")
        subprocess.run([sys.executable, str(ROOT / "build.py")], cwd=ROOT)


if __name__ == "__main__":
    main()
