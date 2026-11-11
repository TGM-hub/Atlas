"""UI checks for the Atlas (lot A). Run: py tools\\test_atlas_ui.py [test names…]
Needs Playwright (py -m pip install playwright). Browser: Edge, or SMOKE_BROWSER=chromium.
Exit code 0 when every test passes, 1 otherwise."""
import os, socket, sys, threading, traceback
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ATLAS = Path(__file__).resolve().parent.parent
BROWSER = None
BASE = None


class Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *a): pass


def serve(root):
    s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
    httpd = ThreadingHTTPServer(("127.0.0.1", port), partial(Quiet, directory=str(root)))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, f"http://127.0.0.1:{port}/"


def page(width, height, hash="", path="index.html", on_request=None, wait="load", errors=None):
    """A fresh browser context (empty storage) on one Atlas page."""
    ctx = BROWSER.new_context(viewport={"width": width, "height": height}, service_workers="block")
    ctx.route(lambda url: not url.startswith(BASE), lambda r: r.fulfill(status=200, content_type="text/html", body=""))   # never leave the machine
    p = ctx.new_page()
    if on_request:
        p.on("request", lambda r: on_request(r.url))
    if errors is not None:
        p.on("pageerror", lambda e: errors.append(str(e)))
    p.goto(BASE + path + hash, wait_until=wait)
    if wait == "load":
        p.wait_for_timeout(350)
    return p


def title(p): return p.inner_text("#panel h1").strip()
def vb(p): return [float(x) for x in p.get_attribute("#map", "viewBox").split()]
def cls(p, iso): return p.evaluate("i => document.querySelector(`#map path[data-iso=\"${i}\"]`).className.baseVal", iso)


def point_on(p, iso):
    """A screen point of the map that is on this country (None when it is out of view)."""
    return p.evaluate("""i => { const r = document.getElementById('mapwrap').getBoundingClientRect();
      for (let y = r.top + 10; y < r.bottom - 10; y += 12) for (let x = r.left + 10; x < r.right - 10; x += 12) {
        const el = document.elementFromPoint(x, y); if (el && el.dataset && el.dataset.iso === i) return [x, y]; }
      return null; }""", iso)


def results(p):
    """Rows of the search list as 'class|text' (text as written, before CSS upper-casing)."""
    return p.evaluate("""() => { const walk = n => n.nodeType === 3 ? n.textContent : [...n.childNodes].map(walk).join(' ');
      return [...document.querySelectorAll('#presults > *')].map(e => e.className.split(' ')[0] + '|' + walk(e).replace(/\\s+/g, ' ').trim()); }""")


def search(p, text):
    p.keyboard.type(text); p.wait_for_timeout(150)


# ---------------------------------------------------------------- T1 header
LONG = ["id", "gb", "ba", "ae", "do", "mp"]   # Indonesia, United Kingdom, Bosnia and Herzegovina, UAE, Dominican Republic, Northern Mariana Islands


def t_header_never_clips():
    for w, h in [(1440, 900), (1024, 768), (390, 844)]:
        for iso in LONG:
            p = page(w, h, "#" + iso)
            bad = p.evaluate("""() => { const pr = document.getElementById('panel').getBoundingClientRect();
              return [...document.querySelectorAll('#panel .head button')].filter(b => { const r = b.getBoundingClientRect();
                return r.right > pr.right + 0.5 || r.left < pr.left - 0.5 || r.width === 0; }).map(b => b.textContent); }""")
            assert bad == [], f"{iso} at {w}px: clipped {bad}"
            p.context.close()


# ---------------------------------------------------------------- T2 Lively
def t_no_lively():
    p = page(1440, 900)
    assert p.evaluate("typeof window.livelyPropertyListener") == "undefined"
    assert "gutter" not in (ATLAS / "index.html").read_text(encoding="utf-8")
    assert "Card of the day" not in p.evaluate("[...document.querySelectorAll('#panel h2')].map(h => h.textContent)")


# ---------------------------------------------------------------- T3 coverage and legend
def t_coverage_levels():
    p = page(1440, 900)
    assert "t1" in cls(p, "FR")                                  # trainers, no card
    assert "c2" in cls(p, "PL") and "t1" not in cls(p, "PL")
    assert "c1" in cls(p, "TR") and "t1" not in cls(p, "TR")
    assert not any(k in cls(p, "CN").split() for k in ("t1", "c1", "c2"))
    assert p.evaluate("getComputedStyle(document.querySelector('#map path[data-iso=\"FR\"]')).fill") == "rgb(79, 127, 143)"


def t_legend_follows_mode():
    p = page(1440, 900)
    text = lambda: p.evaluate("document.getElementById('legend').innerText")
    for label in ("2+ cards", "1 card", "trainer only", "nothing yet"):
        assert label in text(), label
    p.click("#weakToggle")
    assert "accuracy" in text() and "trainer only" not in text()
    assert p.evaluate("!!document.querySelector('#legend .wlegend') && !document.querySelector('#panel .wlegend')")


def t_legend_stays_small_on_phone():
    p = page(390, 844)
    lg, mp = p.evaluate("['legend', 'mapwrap'].map(i => document.getElementById(i).getBoundingClientRect().height)")
    assert lg <= 0.3 * mp, f"legend {lg:.0f}px on a {mp:.0f}px map"
    assert "trainer only" in p.inner_text("#legend")


def t_tooltip_counts_trainers():
    p = page(1440, 900)
    p.mouse.move(*point_on(p, "FR")); p.wait_for_timeout(100)
    tip = " ".join(p.inner_text("#tip").split())
    assert tip.startswith("France") and tip.endswith("4 trainers · no card"), tip


# ---------------------------------------------------------------- T4 country facts
def t_country_facts():
    p = page(1440, 900, "#pl")
    assert p.inner_text("#panel .facts") == "PL · Europe · Tier 1 common · 6 cards · 5 trainers"
    errs = []
    p = page(1440, 900, "#ve", errors=errs)                      # on the map, not in countries.json
    assert p.inner_text("#panel .facts") == "VE · 0 cards · 0 trainers"
    assert "Venezuela" in title(p) and errs == []


def t_trainer_rows_do_not_repeat_country():
    p = page(1440, 900, "#id")
    smalls = p.evaluate("[...document.querySelectorAll('#panel .country-apps > a.app small')].map(s => s.textContent)")
    assert smalls and all("Indonesia" not in s for s in smalls), smalls


# ---------------------------------------------------------------- T5 zoom and fit
def t_zoom_buttons_and_limit():
    p = page(1440, 900)
    w0 = vb(p)[2]; p.click("#zoomIn"); p.wait_for_timeout(250)
    assert abs(vb(p)[2] - w0 / 1.6) < 1, vb(p)
    for _ in range(12): p.click("#zoomIn")
    p.wait_for_timeout(250); assert abs(vb(p)[2] - 2000 / 12) < 1, vb(p)
    p.click("#fit"); p.wait_for_timeout(250); assert vb(p) == [0, 0, 2000, 1040]
    assert p.evaluate("!document.getElementById('recenter')")
    p.keyboard.press("+"); p.wait_for_timeout(250); assert abs(vb(p)[2] - 2000 / 1.6) < 1
    p.keyboard.press("-"); p.wait_for_timeout(250); assert abs(vb(p)[2] - 2000) < 1


def t_fit_on_open_not_on_map_click():
    p = page(1440, 900); search(p, "poland"); p.keyboard.press("Enter"); p.wait_for_timeout(300)
    assert title(p) == "Poland"
    x, y, w, h = vb(p); assert 2000 / 12 - 1 <= w < 600, (x, y, w, h)
    box = p.evaluate("(() => { const b = document.querySelector('#map path[data-iso=\"PL\"]').getBBox(); return { x: b.x, y: b.y, width: b.width, height: b.height }; })()")
    assert x < box["x"] and box["x"] + box["width"] < x + w and y < box["y"] and box["y"] + box["height"] < y + h
    before = vb(p); pt = point_on(p, "DE"); assert pt, "Germany should be in view next to Poland"
    p.mouse.click(*pt); p.wait_for_timeout(300)
    assert title(p) == "Germany" and vb(p) == before


def t_fit_awkward_countries():
    # main landmass of each, in map units (world is 2000 wide): never the whole world, never NaN
    for iso, lo, hi in [("fr", 960, 1060), ("us", 330, 560), ("ru", 1250, 1750), ("mc", 990, 1070)]:
        p = page(1440, 900, "#" + iso); p.wait_for_timeout(300); x, y, w, h = vb(p)
        assert all(v == v for v in (x, y, w, h)) and w < 1300 and x >= 0 and x + w <= 2000.5, f"{iso}: {x, y, w, h}"
        assert lo <= x + w / 2 <= hi, f"{iso}: centre {x + w / 2:.0f}"
        p.context.close()


# ---------------------------------------------------------------- T6 Back and Esc
def t_back_walks_countries():
    p = page(1440, 900)
    for q in ("poland", "czechia", "slovakia"):
        search(p, q); p.keyboard.press("Enter"); p.wait_for_timeout(200)
    assert title(p) == "Slovakia"
    p.go_back(); p.wait_for_timeout(200); assert title(p) == "Czechia"
    p.go_back(); p.wait_for_timeout(200); assert title(p) == "Poland"
    p.go_back(); p.wait_for_timeout(200); assert title(p) == "Atlas"
    p.go_forward(); p.wait_for_timeout(200); assert title(p) == "Poland"


def t_escape_layers():
    p = page(1440, 900, "#pl")
    p.click("header .chip:has-text('Road lines')"); p.wait_for_timeout(150)
    p.keyboard.press("Escape"); p.wait_for_timeout(150)
    assert title(p) == "Road lines", title(p)                    # country closed, filter kept
    assert p.evaluate("document.querySelector('header .chip.on b').textContent") == "Road lines"
    p.keyboard.press("Escape"); p.wait_for_timeout(150)
    assert title(p) == "Atlas"


def t_odd_addresses():
    for h, want in [("#fr", "France"), ("#FR", "France"), ("#zz", "Atlas"), ("#pl/cz", "Atlas"), ("", "Atlas")]:
        errs = []; p = page(1440, 900, h, errors=errs)
        assert title(p) == want and errs == [], (h, title(p), errs)
        p.context.close()
    p = page(1440, 900, "#zz"); search(p, "poland"); p.keyboard.press("Enter"); p.wait_for_timeout(200)
    p.go_back(); p.wait_for_timeout(200); assert title(p) == "Atlas"


# ---------------------------------------------------------------- T7 search
def t_search_trainer_for_country():
    p = page(1440, 900); search(p, "bollard france"); r = results(p)
    assert r[0] == "pgrp|Trainers" and r[1].startswith("pr|") and "Bollards · France" in r[1] and "↗" in r[1], r
    assert not any("French Guiana" in x or "French Polynesia" in x for x in r), r
    assert any("France" in x and "4 trainers · no card yet" in x for x in r), r
    with p.context.expect_page() as new: p.keyboard.press("Enter")
    assert new.value.url == "https://tgm-hub.github.io/bollards-trainer/#fr", new.value.url
    assert not p.evaluate("document.getElementById('palette').classList.contains('open')")


def t_search_cards_first_for_clue_queries():
    p = page(1440, 900); search(p, "phone br"); r = results(p)
    assert r[0] == "pgrp|Cards" and "Brazil" in r[1], r
    p.keyboard.press("Enter"); p.wait_for_timeout(200)
    assert p.evaluate("document.getElementById('lightbox').classList.contains('open')")


def t_search_country_name_opens_country():
    p = page(1440, 900); search(p, "poland"); r = results(p)
    assert r[0] == "pgrp|Countries" and "Poland" in r[1] and "5 trainers · 6 cards" in r[1], r
    assert "pgrp|Cards" in r


def t_search_references_and_recent():
    p = page(1440, 900); search(p, "plonk jp")
    assert any(x.startswith("pr|") and "Plonk It · Japan" in x and "↗" in x for x in results(p)), results(p)
    p.keyboard.press("Escape")
    for q in ("poland", "japan"):
        search(p, q); p.keyboard.press("Enter"); p.wait_for_timeout(200)
    p.click("#searchBtn"); p.wait_for_timeout(150); r = results(p)
    assert r[0] == "pgrp|Recent" and "Japan" in r[1] and "Poland" in r[2], r
    assert "bollard france" in p.inner_text("#phelp")


def t_search_robust():
    errs = []
    for seed in ('"nope"', '{"a":1}', '["ZZ","PL",5]'):
        p = page(1440, 900, errors=errs)
        p.evaluate("v => localStorage.setItem('atlas.recent', v)", seed); p.reload(); p.wait_for_timeout(300)
        p.click("#searchBtn"); p.wait_for_timeout(120)
        assert p.evaluate("document.getElementById('palette').classList.contains('open')")
    assert "Poland" in " ".join(results(p)) and "ZZ" not in " ".join(results(p)), results(p)
    for q in ("x", "qqqqqq", "indonésie", "plate trainer regions"):
        p = page(1440, 900, errors=errs); search(p, q)
    assert any("Plate Trainer – regions" in x and "↗" in x for x in results(p)), results(p)
    assert errs == [], errs


# ---------------------------------------------------------------- T8 relief
def t_relief_is_lazy():
    seen = []
    p = page(1440, 900, on_request=seen.append, wait="domcontentloaded")
    assert p.evaluate("document.querySelectorAll('#map path').length") > 200
    assert not any(u.endswith("relief.webp") for u in seen), "relief requested before the map was drawn"
    p.wait_for_timeout(2000); assert any(u.endswith("relief.webp") for u in seen), "relief never requested"
    phone = []
    q = page(390, 844, on_request=phone.append); q.wait_for_timeout(2000)
    assert not any(u.endswith("relief.webp") for u in phone), "relief requested on a phone-width screen"


# ---------------------------------------------------------------- T9 regions
MOVED = "ID Indonesia/other/Provinces.png"; NEW = "ID Indonesia/regions/Provinces.png"


def t_regions_type():                       # needs data.js rebuilt by build.cmd after the files were moved
    p = page(1440, 900)
    assert p.evaluate("window.ATLAS.types.some(t => t.key === 'regions')"), "run build.cmd first"
    assert p.evaluate("window.ATLAS.cards.filter(c => c.types.includes('regions')).length") >= 7
    assert p.evaluate("window.ATLAS.cards.filter(c => c.types.includes('regions')).every(c => !!c.src)"), "a Regions card has no source"
    assert not p.evaluate("window.ATLAS.cards.some(c => c.types.includes('other') && /Provinces|Kabupaten|Régions/.test(c.id))")
    chips = p.evaluate("[...document.querySelectorAll('header .chip b')].map(b => b.textContent)")
    assert chips.index("Regions") == chips.index("Phone codes") + 1, chips


def t_ids_migrate():
    for html in ("index.html", "quiz.html"):
        p = page(1440, 900, path=html)
        p.evaluate("""([o]) => { localStorage.setItem('atlas.quiz', JSON.stringify({ [o]: [3, 2, 1, 9e12, 0, 0], 'BR Brazil/phone/Indicatifs DDD.png': [1, 1, 1, 9e12, 0, 0] }));
                               localStorage.setItem('atlas.inv', JSON.stringify({ [o]: true })); }""", [MOVED])
        p.reload(); p.wait_for_timeout(300)
        quiz = p.evaluate("JSON.parse(localStorage.getItem('atlas.quiz'))"); inv = p.evaluate("JSON.parse(localStorage.getItem('atlas.inv'))")
        assert NEW in quiz and MOVED not in quiz and quiz[NEW][0] == 3 and "BR Brazil/phone/Indicatifs DDD.png" in quiz, (html, quiz)
        assert inv == {NEW: True}, (html, inv)
        p.reload(); p.wait_for_timeout(300)
        assert p.evaluate("JSON.parse(localStorage.getItem('atlas.quiz'))")[NEW][0] == 3


# ---------------------------------------------------------------- runner
def main(argv):
    global BROWSER, BASE
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Playwright missing: py -m pip install playwright"); return 3
    tests = {k: v for k, v in globals().items() if k.startswith("t_") and callable(v)}
    names = argv or list(tests)
    unknown = [n for n in names if n not in tests]
    if unknown:
        print("Unknown test:", ", ".join(unknown)); return 1
    httpd, BASE = serve(ATLAS)
    failed = 0
    with sync_playwright() as pw:
        kind = os.environ.get("SMOKE_BROWSER", "msedge")
        BROWSER = pw.chromium.launch(**({} if kind == "chromium" else {"channel": kind}))
        for n in names:
            try:
                tests[n](); print("PASS", n)
            except Exception as e:
                failed += 1
                msg = str(e).strip().splitlines()[0] if str(e).strip() else "assert failed: " + (traceback.extract_tb(e.__traceback__)[-1].line or "")
                print(f"FAIL {n}: {msg[:300]}")
            for c in list(BROWSER.contexts): c.close()
        BROWSER.close()
    httpd.shutdown()
    print(f"{len(names) - failed}/{len(names)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
