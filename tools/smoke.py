"""Tests de fumée avant publication : l'Atlas et les trainers, chacun depuis son dossier local.

    python tools/smoke.py                      # tous les repos connus
    python tools/smoke.py phone-codes Atlas    # seulement ceux-là (nom du dossier)
    python tools/smoke.py --static             # sans navigateur (contrôles de données seulement)

Pour chaque repo :
  1. données : JSON valides, fichiers locaux référencés présents, tgm-core.js identique à celui de l'Atlas ;
  2. navigateur (Edge via Playwright, sans fenêtre), bureau 1440x900 puis mobile 390x844 :
     la page charge sans erreur JavaScript ni fichier local manquant (404), une manche est jouée et
     l'historique du trainer change, les liens directs (#pays, #mode) arrivent au bon endroit.
Code de retour 0 si tout passe, 1 sinon ; captures des pages en faute dans _private_cache/smoke/.
publish-all.ps1 le lance avant chaque repo et ne publie pas un repo en échec.

Prérequis navigateur : pip install playwright   (Edge déjà installé ; SMOKE_BROWSER=chromium pour un Chromium Playwright)
"""
import json
import os
import re
import socket
import sys
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ATLAS = Path(__file__).resolve().parent.parent
HOME = Path(os.environ.get("SMOKE_HOME") or Path.home())
SHOTS = ATLAS / "_private_cache" / "smoke"
VIEWPORTS = {"desktop": (1440, 900), "mobile": (390, 844)}

# ---------------------------------------------------------------- what each page must do
# page: file to open ; play: JS run in the page to give one answer (may be async) ; changes: localStorage keys that
# must change after the answer ; links: [hash, JS predicate that must become true]
JS_CLICK_CENTER = """sel => { const e = document.querySelector(sel); if (!e) return false; const r = e.getBoundingClientRect();
  const x = r.left + r.width / 2, y = r.top + r.height / 2;
  for (const t of ['pointerdown', 'mousedown', 'pointerup', 'mouseup', 'click'])
    e.dispatchEvent(new (t.startsWith('pointer') ? PointerEvent : MouseEvent)(t, { bubbles: true, clientX: x, clientY: y, pointerId: 1, button: 0 }));
  return true; }"""
APPS = {
    "Atlas": {"dir": ATLAS, "pages": [
        {"page": "index.html", "links": [["#fr", "document.querySelector('#panel h1')?.textContent.trim() === 'France'"],
                                         ["#ua", "[...document.querySelectorAll('#panel a.app')].some(a => a.href.includes('russian-pannels-learning/#explore/ua'))"],
                                         ["", "(() => { document.getElementById('weakToggle').click(); const ok = document.getElementById('weakToggle').classList.contains('on') && !!document.querySelector('#panel .wlegend'); document.getElementById('weakToggle').click(); return ok; })()"]]},
        {"page": "daily.html", "links": [["", "document.querySelectorAll('#perApp tr').length >= 9"]]},
        {"page": "quiz.html", "play": "async () => { document.getElementById('flip').click(); document.querySelector('#acts button[data-r=\"2\"]').click(); }",
         "changes": ["atlas.quiz", "tgm.stats.atlas-quiz"], "links": [["#br", "document.getElementById('fIso').textContent.includes('Brazil')"]]},
        {"page": "compare.html", "links": [["#pl/cz", "document.getElementById('selA').value === 'PL' && document.getElementById('selB').value === 'CZ' && document.querySelectorAll('#out section').length >= 3"]]},
        {"page": "confusions.html", "links": [["", "!!document.querySelector('#period button.on')"], ["#pl", "document.querySelector('#isof').textContent.includes('Poland')"]]},
    ]},
    "phone-codes": {"pages": [{"page": "index.html",
        "play": "async () => { for (let i = 0; i < 40 && !(window.round && round.target); i++) await new Promise(r => setTimeout(r, 100)); finish(false, 'smoke test', ''); }",
        "changes": ["phonecodes.hist", "tgm.stats.phone-codes"],
        "links": [["#br", "typeof C !== 'undefined' && C && C.iso === 'BR'"], ["#jp", "typeof C !== 'undefined' && C && C.iso === 'JP'"]]}]},
    "plate-trainer": {"pages": [{"page": "index.html",
        "play": "async () => { document.querySelector('#start').click(); await new Promise(r => setTimeout(r, 300)); document.querySelector('.opt').click(); }",
        "changes": ["plateTrainer.hist", "tgm.stats.plate-trainer"],
        "links": [["#fr", "document.body.innerText.includes('France')"], ["#r-mx", "document.body.innerText.includes('Mexico')"]]}]},
    "bollards-trainer": {"pages": [{"page": "index.html",
        "play": "async () => { await new Promise(r => setTimeout(r, 300)); document.querySelector('.choice').click(); }",
        "changes": ["bollard-trainer-v1", "tgm.stats.bollards"],
        "links": [["#fr", "!document.querySelector('#sheet').hidden"]]}]},
    "city-placer": {"pages": [{"page": "index.html", "wait": 2500,
        "play": "async () => { const m = window.__cpMap; await new Promise(r => m.loaded() ? r() : m.once('load', r)); const c = m.getCanvas().getBoundingClientRect(); m.fire('click', { point: { x: c.width / 2, y: c.height / 2 }, lngLat: m.getCenter(), originalEvent: new MouseEvent('click') }); }",
        "changes": ["cp.srs"],
        "links": [["#fr", "[...document.querySelectorAll('select')].some(s => s.value === 'FR')"], ["#w", "document.body.innerText.length > 0"],
                  ["#explore/fr", "document.body.classList.contains('exploring') && document.getElementById('crumbs').textContent.includes('France')"]]}]},
    "script-identifier-geoguessr": {"pages": [{"page": "index.html",
        "play": "async () => { await new Promise(r => setTimeout(r, 300)); if (round && round.kind === 'map') { mapPick = round.target.z[0]; answerMap(); return; } document.querySelector('#options .opt:not(.hedge):not(:disabled)').click(); }",
        "changes": ["signreader.v2"],
        "links": [["#ru", "document.body.innerText.includes('Russian')"]]}]},
    "vietnam-province-guesser": {"pages": [{"page": "index.html",
        "play": "async () => { await new Promise(r => setTimeout(r, 300)); if (typeof finish === 'function') { finish(false, 'smoke test'); return; } const k = 'tinhvn.v1', s0 = localStorage.getItem(k); for (let i = 0; i < 4 && localStorage.getItem(k) === s0; i++) { (" + JS_CLICK_CENTER + ")('#mapsvg path'); await new Promise(r => setTimeout(r, 150)); document.querySelector('#btn-ok').click(); await new Promise(r => setTimeout(r, 300)); } }",
        "changes": ["tinhvn.v1", "tgm.stats.vietnam"],
        "links": [["#vn", "document.querySelector('#ov-study').classList.contains('open')"]]}]},
    "indonesia-kabupaten": {"pages": [{"page": "index.html",
        "play": "async () => { await new Promise(r => setTimeout(r, 300)); (" + JS_CLICK_CENTER + ")('#units path.act'); }",
        "changes": ["idkab.v1.stats", "tgm.stats.kabupaten"],
        "links": [["#plate/java", "document.querySelector('#modes .on')?.dataset.m === 'plate' && document.getElementById('zone').value === 'i:Java'"],
                  ["#explore", "document.querySelector('#modes .on')?.dataset.m === 'explore'"]]}]},
    "russian-pannels-learning": {"pages": [{"page": "index.html",
        "play": "async () => { const g = document.getElementById('guess'); g.value = 'moskva'; document.getElementById('submit').click(); await new Promise(r => setTimeout(r, 300)); (" + JS_CLICK_CENTER + ")('#gReg [data-id]'); }",
        "changes": ["cyrL"],
        "links": [["#ua", "document.querySelector('#filter .on')?.dataset.f === 'OTHER'"], ["#regions", "document.querySelector('#mode .on')?.dataset.m === 'reg'"],
                  ["#explore/ua", "document.body.classList.contains('exploring') && document.getElementById('expC').value === 'UKR' && document.querySelectorAll('#expList button').length > 0"]]}]},
    # reads plates and bollards from the sibling repos: served from the parent folder, like on GitHub Pages
    "clue-fusion": {"siblings": True, "pages": [{"page": "index.html", "wait": 1800,
        "play": "async () => { document.querySelector('.opt').click(); }",
        "changes": ["cluefusion.hist", "tgm.stats.clue-fusion"],
        "links": [["", "window.__cf && __cf.counts.plates > 0 && __cf.counts.bollards > 0 && __cf.counts.langs > 0 && document.querySelectorAll('.clue').length >= 2"],
                  ["#pl", "(() => { document.querySelector('.opt').click(); return document.querySelector('.verdict').textContent.includes('Poland'); })()"],
                  ["#explore/pl", "!document.querySelector('#exp').hidden && document.querySelectorAll('#exp .clue').length > 0"]]}]},
}


def repo_dir(name):
    return APPS[name].get("dir") or HOME / name


# ---------------------------------------------------------------- static checks
SKIP_DIRS = {".git", "_commons", "_private_cache", "_inbox", "_to_delete", "node_modules", "images", "thumbs", "__pycache__", "Claude outputs"}


def walk(root, exts):
    for p in root.rglob("*"):
        if p.is_file() and p.suffix.lower() in exts and not (set(p.relative_to(root).parts[:-1]) & SKIP_DIRS):
            yield p


def static_checks(name, root):
    errs = []
    for p in walk(root, {".json"}):
        try:
            json.loads(p.read_text(encoding="utf-8"))
        except Exception as e:
            errs.append(f"JSON invalide : {p.relative_to(root)} ({e})")
    for p in sorted(root.glob("*.html")):          # published pages only (src/ templates are not served)
        txt = p.read_text(encoding="utf-8")
        for ref in re.findall(r'<(?:script|link|img)\b[^>]*?\b(?:src|href)="([^"#?]+)"', txt):
            if re.match(r"^(https?:|data:|//|mailto:)", ref) or "${" in ref:
                continue
            if not (p.parent / ref).exists():
                errs.append(f"{p.relative_to(root)} : fichier référencé absent {ref}")
    core = ATLAS / "tgm-core.js"
    if name != "Atlas" and (root / "tgm-core.js").exists() and core.exists() and (root / "tgm-core.js").read_bytes() != core.read_bytes():
        errs.append("tgm-core.js différent de celui de l'Atlas (relancer build.cmd dans l'Atlas)")
    # images référencées par les données
    if name == "plate-trainer":
        for js in [root / "data" / "plates.js", *sorted((root / "data" / "regions").glob("*.js"))]:
            imgs = re.findall(r'"?img"?\s*:\s*"([^"]+)"', js.read_text(encoding="utf-8"))
            missing = [i for i in imgs if not (root / i).exists()]
            if missing:
                errs.append(f"{js.relative_to(root)} : {len(missing)} image(s) absente(s), ex. {missing[:3]}")
    if name == "bollards-trainer":
        m = re.search(r'"imageDir":"([^"]*)"', (root / "index.html").read_text(encoding="utf-8"))
        idir = m.group(1) if m else "images/"
        data = json.loads((root / "bollards.json").read_text(encoding="utf-8")) if (root / "bollards.json").exists() else {"entries": []}
        missing = [e["file"] for e in data.get("entries", []) if e.get("file") and not (root / idir / e["file"]).exists()]
        if missing:
            errs.append(f"bollards : {len(missing)} image(s) absente(s), ex. {missing[:3]}")
    if name == "Atlas":
        dj = (root / "data.js").read_text(encoding="utf-8")
        data = json.loads(dj[dj.index("=") + 1:].strip().rstrip(";"))
        for c in data["cards"]:
            for f in (c["thumb"], c["file"]):
                if not (root / f).exists():
                    errs.append(f"data.js : {c['id']} → {f} absent (relancer build.cmd)")
    return errs


# ---------------------------------------------------------------- browser checks
class Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *a): pass


def serve(root):
    s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
    httpd = ThreadingHTTPServer(("127.0.0.1", port), partial(Quiet, directory=str(root)))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, f"http://127.0.0.1:{port}/"


def browser_checks(name, root, pw, routes=None):
    errs = []
    sib = APPS[name].get("siblings")
    httpd, base = serve(root.parent if sib else root)
    pre = root.name + "/" if sib else ""
    kind = os.environ.get("SMOKE_BROWSER", "msedge")
    browser = pw.chromium.launch(**({} if kind == "chromium" else {"channel": kind}))
    try:
        for vp, (w, h) in VIEWPORTS.items():
            for spec in APPS[name]["pages"]:
                ctx = browser.new_context(viewport={"width": w, "height": h})
                if routes:
                    routes(ctx)
                page = ctx.new_page()
                found = []
                page.on("pageerror", lambda e: found.append(f"erreur JS : {str(e)[:160]}"))
                page.on("response", lambda r: r.status >= 400 and r.url.startswith(base + pre)
                        and found.append(f"{r.status} {r.url[len(base):]}"))
                label = f"{name}/{spec['page']} [{vp}]"
                page.goto(base + pre + spec["page"], wait_until="load")
                page.wait_for_timeout(spec.get("wait", 1200))
                if spec.get("play"):
                    before = page.evaluate("ks => ks.map(k => localStorage.getItem(k))", spec["changes"])
                    try:
                        page.evaluate(spec["play"])
                        page.wait_for_timeout(700)
                    except Exception as e:
                        found.append(f"manche impossible : {str(e).splitlines()[0][:160]}")
                    after = page.evaluate("ks => ks.map(k => localStorage.getItem(k))", spec["changes"])
                    for k, a, b in zip(spec["changes"], before, after):
                        if a == b:
                            found.append(f"après une réponse, {k} n'a pas changé")
                for hsh, pred in spec.get("links", []):
                    page.goto("about:blank")                      # a hash-only change would not reload the page
                    page.goto(base + pre + spec["page"] + hsh, wait_until="load")
                    page.wait_for_timeout(spec.get("wait", 1200))
                    try:
                        page.wait_for_function(pred, timeout=4000)
                    except Exception:
                        found.append(f"lien direct {hsh or '(page)'} : la page n'arrive pas au bon endroit")
                if found:
                    SHOTS.mkdir(parents=True, exist_ok=True)
                    shot = SHOTS / f"{name}-{spec['page'].replace('.html', '')}-{vp}.png"
                    page.screenshot(path=str(shot))
                    errs += [f"{label} : {f}" for f in dict.fromkeys(found)] + [f"{label} : capture {shot}"]
                ctx.close()
    finally:
        browser.close(); httpd.shutdown()
    return errs


def main(argv, routes=None):
    static_only = "--static" in argv
    names = [a for a in argv if not a.startswith("--")] or list(APPS)
    names = [Path(n).name if Path(n).name in APPS else n for n in names]
    unknown = [n for n in names if n not in APPS]
    if unknown:
        print(f"inconnu(s) : {unknown} ; repos testés : {', '.join(APPS)}"); return 2
    pw_ctx = None
    if not static_only:
        try:
            from playwright.sync_api import sync_playwright
            pw_ctx = sync_playwright().start()
        except ImportError:
            print("Playwright absent : pip install playwright  (ou --static pour les seuls contrôles de données)"); return 3
    failed = False
    try:
        for n in names:
            root = repo_dir(n)
            if not root.exists():
                print(f"· {n} : dossier absent ({root}), ignoré"); continue
            errs = static_checks(n, root)
            if pw_ctx and not errs:
                errs = browser_checks(n, root, pw_ctx, routes)
            print(("✗ " if errs else "✓ ") + n)
            for e in errs:
                print("    " + e)
            failed |= bool(errs)
    finally:
        if pw_ctx:
            pw_ctx.stop()
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
