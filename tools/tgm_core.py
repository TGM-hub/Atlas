"""countries.json -> tgm-core.js (Atlas), puis rafraîchit les copies des trainers.

Appelé par build.py ; lançable seul : python tools/tgm_core.py
Les trainers qui utilisent le cœur en gardent une copie (tgm-core.js à la racine de leur repo) :
elle est remplacée quand elle existe, jamais créée d'office.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent          # ...\Desktop\Atlas
TEMPLATE = ROOT / "tools" / "tgm-core.template.js"
CONTINENTS = {"EU", "AS", "AF", "NA", "SA", "OC"}
KEYS = {"en", "fr", "continent", "tier", "plonkit", "sv"}


def load(problems, warnings):
    path = ROOT / "countries.json"
    if not path.exists():
        problems.append("countries.json absent : tgm-core.js non généré")
        return None
    doc = json.loads(path.read_text(encoding="utf-8"))
    cs = doc.get("countries", {})
    for iso, c in cs.items():
        where = f"countries.json [{iso}]"
        if not re.fullmatch(r"[A-Z]{2}", iso):
            problems.append(f"{where} : code ISO invalide")
        miss = KEYS - set(c)
        if miss:
            problems.append(f"{where} : champ(s) manquant(s) {sorted(miss)}")
        if c.get("tier") not in (1, 2, 3, 4):
            problems.append(f"{where} : tier doit valoir 1 à 4")
        if c.get("continent") not in CONTINENTS:
            problems.append(f"{where} : continent « {c.get('continent')} » inconnu ({' '.join(sorted(CONTINENTS))})")
        p = c.get("plonkit")
        if p is not None and not re.fullmatch(r"[a-z0-9-]+", p):
            problems.append(f"{where} : slug Plonk It invalide « {p} »")
        sv = c.get("sv")
        if sv is not None and not (isinstance(sv, list) and len(sv) == 3 and all(isinstance(x, (int, float)) for x in sv)):
            problems.append(f"{where} : sv doit être [lat, lon, zoom]")
    return doc


def build(apps=(), problems=None, warnings=None, quiet=False):
    problems = [] if problems is None else problems
    warnings = [] if warnings is None else warnings
    n0 = len(problems)
    doc = load(problems, warnings)
    if doc is None or len(problems) > n0:
        return problems, warnings
    cs = doc["countries"]
    for a in apps:
        out = [c for c in a.get("countries", []) if c not in cs]
        if out:
            warnings.append(f"apps.json [{a.get('id')}] : pays absents de countries.json {out}")
    data = {k: {f: cs[k][f] for f in ("en", "fr", "continent", "tier", "plonkit", "sv")} for k in sorted(cs)}
    js = (TEMPLATE.read_text(encoding="utf-8")
          .replace("/*VERSION*/", str(doc.get("updated", "")))
          .replace("/*COUNTRIES*/", json.dumps(data, ensure_ascii=False, separators=(",", ":"))))
    core = ROOT / "tgm-core.js"
    if not core.exists() or core.read_text(encoding="utf-8") != js:
        core.write_text(js, encoding="utf-8", newline="\n")
        quiet or print(f"tgm-core.js régénéré ({len(cs)} pays).")
    # copies des trainers (repos voisins dans le dossier utilisateur)
    home = Path.home()
    for repo in sorted({a["repo"].split("/")[-1] for a in apps if a.get("repo")}):
        dst = home / repo / "tgm-core.js"
        if dst.exists() and dst.read_text(encoding="utf-8") != js:
            dst.write_text(js, encoding="utf-8", newline="\n")
            quiet or print(f"  copie mise à jour : {repo}/tgm-core.js")
    return problems, warnings


if __name__ == "__main__":
    apps_file = ROOT / "apps.json"
    apps = json.loads(apps_file.read_text(encoding="utf-8"))["apps"] if apps_file.exists() else []
    p, w = build(apps)
    for x in w:
        print("  -", x)
    for x in p:
        print("  !", x)
    sys.exit(1 if p else 0)
