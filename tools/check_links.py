"""Vérifie les liens sortants de l'Atlas : trainers (apps.json), pages Plonk It (countries.json),
maps LearnableMeta (learnable.js). Lent et poli : une requête toutes les 1,5 s, résultats gardés
7 jours dans _private_cache/links.json (ignoré par Git), donc un second passage ne refait rien.

    python tools/check_links.py            # tout
    python tools/check_links.py --only plonkit|apps|learnable
    python tools/check_links.py --fresh    # ignore le cache

Ne fait pas partie du build (qui reste hors ligne). Sortie : liste des liens en échec, code de retour 1 s'il y en a.
"""
import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "_private_cache" / "links.json"
TTL = 7 * 86400
DELAY = 1.5
UA = "TGM-Atlas-linkcheck/1.0 (personal GeoGuessr atlas; one request every 1.5 s)"


def targets(only):
    out = []
    if only in (None, "apps"):
        for a in json.loads((ROOT / "apps.json").read_text(encoding="utf-8"))["apps"]:
            if a.get("status") not in ("live", "wip"):
                continue
            out.append(("apps", a["id"], a["url"]))
            if a.get("deeplink") and a.get("countries"):
                out.append(("apps", a["id"] + " #" + a["countries"][0].lower(), a["deeplink"].replace("{iso}", a["countries"][0].lower())))
    if only in (None, "plonkit"):
        cs = json.loads((ROOT / "countries.json").read_text(encoding="utf-8"))["countries"]
        for iso, c in sorted(cs.items()):
            if c.get("plonkit"):
                out.append(("plonkit", iso, "https://www.plonkit.net/" + c["plonkit"]))
    if only in (None, "learnable"):
        txt = (ROOT / "learnable.js").read_text(encoding="utf-8")
        for mid in sorted(set(re.findall(r'\["([0-9a-f]{24})"', txt))):
            out.append(("learnable", mid, "https://learnablemeta.com/maps/" + mid))
    return out


def check(url):
    for method in ("HEAD", "GET"):
        req = urllib.request.Request(url, method=method, headers={"User-Agent": UA})
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                return r.status
        except urllib.error.HTTPError as e:
            if method == "HEAD" and e.code in (403, 405, 501):
                continue          # certains serveurs refusent HEAD : on retente en GET
            return e.code
        except Exception as e:
            return f"err: {type(e).__name__}"
    return "err"


def main():
    only = sys.argv[sys.argv.index("--only") + 1] if "--only" in sys.argv else None
    fresh = "--fresh" in sys.argv
    cache = {} if fresh or not CACHE.exists() else json.loads(CACHE.read_text(encoding="utf-8"))
    now = time.time()
    todo = targets(only)
    bad = []
    asked = 0
    for kind, label, url in todo:
        hit = cache.get(url)
        if not hit or now - hit["t"] > TTL:
            if asked:
                time.sleep(DELAY)
            hit = {"status": check(url), "t": now}
            if isinstance(hit["status"], int):   # réseau en panne : on ne garde pas l'échec en cache
                cache[url] = hit
            asked += 1
            CACHE.parent.mkdir(exist_ok=True)
            CACHE.write_text(json.dumps(cache, indent=0), encoding="utf-8")
        if hit["status"] != 200:
            bad.append((kind, label, url, hit["status"]))
    print(f"{len(todo)} lien(s) vérifié(s), {asked} requête(s) faite(s), {len(todo) - asked} depuis le cache.")
    for kind, label, url, st in bad:
        print(f"  ✗ [{kind}] {label} : {st}  {url}")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
