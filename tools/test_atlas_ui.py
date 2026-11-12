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


class Server(ThreadingHTTPServer):
    def handle_error(self, request, client_address):      # a page closed in the middle of a download is not an error
        if not isinstance(sys.exc_info()[1], ConnectionError):
            super().handle_error(request, client_address)


def serve(root):
    s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
    httpd = Server(("127.0.0.1", port), partial(Quiet, directory=str(root)))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, f"http://127.0.0.1:{port}/"


def page(width, height, hash="", path="index.html", on_request=None, wait="load", errors=None, data=None, host=None, storage=None):
    """A fresh browser context (empty storage) on one Atlas page."""
    ctx = BROWSER.new_context(viewport={"width": width, "height": height}, service_workers="block")
    ctx.route(lambda url: not url.startswith(BASE), lambda r: r.fulfill(status=200, content_type="text/html", body=""))   # never leave the machine
    if host:                                   # the same files, seen as a public site (not localhost)
        ctx.route(host + "**", lambda r: r.fulfill(response=ctx.request.get(BASE + r.request.url[len(host):].split("#")[0])))
    if data:
        with_data(ctx, data)
    if storage:                                # localStorage set before the page's own scripts run
        ctx.add_init_script("(() => { const s = %s; for (const k in s) if (localStorage.getItem(k) === null) localStorage.setItem(k, s[k]); })()" % __import__("json").dumps(storage))
    p = ctx.new_page()
    p.set_default_timeout(5000)                # a missing element fails fast instead of waiting 30 s
    if on_request:
        p.on("request", lambda r: on_request(r.url))
    if errors is not None:
        p.on("pageerror", lambda e: errors.append(str(e)))
    p.goto((host or BASE) + path + hash, wait_until=wait)
    if wait == "load":
        p.wait_for_timeout(350)
    return p


def with_data(p_ctx, edit):
    """Serve data.js with the cards edited by `edit(cards)` (tests must not depend on the real dates of the cards)."""
    import json
    src = (ATLAS / "data.js").read_text(encoding="utf-8"); i, j = src.index("{"), src.rindex("}") + 1
    data = json.loads(src[i:j]); edit(data["cards"])
    body = src[:i] + json.dumps(data, ensure_ascii=False) + src[j:]
    p_ctx.route("**/data.js", lambda r: r.fulfill(status=200, content_type="text/javascript; charset=utf-8", body=body))


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
              return [...document.querySelectorAll('#panel .head button')].filter(b => getComputedStyle(b).display !== 'none').filter(b => { const r = b.getBoundingClientRect();
                return r.right > pr.right + 0.5 || r.left < pr.left - 0.5 || r.width === 0; }).map(b => b.textContent); }""")
            assert bad == [], f"{iso} at {w}px: clipped {bad}"
            assert p.evaluate("document.querySelector('#panel h1').getBoundingClientRect().height") < 60 or iso in ("ba", "mp", "do", "ae", "gb"), f"{iso} at {w}px: title broken over lines"
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
    p.click("#colourBy [data-c=accuracy]")
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
    links = p.evaluate("[...document.querySelectorAll('#panel .trainers a.app')].map(s => s.textContent)")
    assert links and all("· Indonesia" not in s for s in links), links


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
    p.click("#clues .chip:has-text('Road lines')"); p.wait_for_timeout(150)
    p.keyboard.press("Escape"); p.wait_for_timeout(150)
    assert title(p) == "Road lines", title(p)                    # country closed, filter kept
    assert p.evaluate("document.querySelector('#clues .chip.on b').textContent") == "Road lines"
    p.keyboard.press("Escape"); p.wait_for_timeout(150)
    assert title(p) == "Atlas"


def t_odd_addresses():
    for h, want in [("#fr", "France"), ("#FR", "France"), ("#zz", "Atlas"), ("#pl/cz", "Poland"), ("", "Atlas")]:
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
    # The browser's own timeline: the relief must start downloading after the page's load event, whatever the machine's speed
    p = page(1440, 900); p.wait_for_timeout(2500)
    start, loaded, paths = p.evaluate("""() => { const r = performance.getEntriesByType('resource').find(e => e.name.endsWith('relief.webp'));
      return [r ? r.startTime : null, performance.getEntriesByType('navigation')[0].loadEventStart, document.querySelectorAll('#map path').length]; }""")
    assert paths > 200
    assert start is not None, "relief never requested"
    assert start >= loaded, f"relief requested at {start:.0f} ms, before the load event ({loaded:.0f} ms)"
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
    chips = p.evaluate("[...document.querySelectorAll('#clues .chip b')].map(b => b.textContent)")
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


# ================================================================ lot B
# ---------------------------------------------------------------- B1 cities
def t_cities_type():                      # needs data.js rebuilt by build.cmd
    p = page(1440, 900)
    keys = p.evaluate("window.ATLAS.types.map(t => t.key)")
    assert "cities" in keys and keys.index("cities") == keys.index("regions") + 1, "run build.cmd first"
    assert p.evaluate("window.ATLAS.apps.find(a => a.id === 'city-placer').types") == ["cities"]


# ---------------------------------------------------------------- B2 header and clue filter
TYPES = ["Landscape", "Language", "Architecture", "Plates", "Bollards", "Poles", "Signs", "Road lines", "Phone codes", "Regions", "Cities", "Google car", "Soil", "Flags", "Other"]


def clue_labels(p): return p.evaluate("[...document.querySelectorAll('#clues .chip b')].map(b => b.textContent)")
def chip(p, label, what): return p.evaluate("([l, w]) => { const c = [...document.querySelectorAll('#clues .chip')].find(c => c.querySelector('b').textContent === l); return w === 'class' ? c.className : w === 'disabled' ? c.disabled : c.textContent.replace(/\\s+/g, ' ').trim(); }", [label, what])


def t_header_three_zones():
    p = page(1440, 900)
    assert p.evaluate("[...document.querySelectorAll('#pages a')].map(a => a.textContent.trim())") == ["Explore", "Review", "Duels", "Mix-ups", "Quiz"]
    assert p.evaluate("document.querySelector('#pages a[aria-current=page]').textContent.trim()") == "Explore"
    assert p.evaluate("!document.getElementById('cmpLink') && !document.getElementById('weakToggle')")
    assert p.evaluate("document.querySelector('header').getBoundingClientRect().height") <= 60
    assert not p.is_visible("#darkToggle"); p.click("#settingsBtn"); assert p.is_visible("#darkToggle")
    before = p.evaluate("localStorage.getItem('atlas.dark')"); p.click("#darkToggle")
    assert p.evaluate("localStorage.getItem('atlas.dark')") != before
    assert p.get_attribute("#darkToggle", "aria-checked") == "false"


def t_clues_never_move():
    want = ["All"] + TYPES + ["Cyrillic"]
    home = page(1440, 900); assert clue_labels(home) == want, clue_labels(home)
    for h in ("#fr", "#id", "#ve"):
        p = page(1440, 900, h); assert clue_labels(p) == want, h
    fr = page(1440, 900, "#fr")
    assert "zero" in chip(fr, "Road lines", "class") and "zero" not in chip(fr, "Bollards", "class")
    assert chip(fr, "Bollards", "text").endswith("trainer"), chip(fr, "Bollards", "text")
    assert chip(home, "Soil", "disabled") and not chip(home, "Plates", "disabled")


def t_clue_click_only_filters():
    p = page(1440, 900, "#fr"); n = len(p.context.pages)
    p.click("#clues .chip:has-text('Bollards')"); p.wait_for_timeout(300)
    assert len(p.context.pages) == n                                  # no tab opened
    assert p.evaluate("document.querySelector('#clues .chip.on b').textContent") == "Bollards"
    assert title(p) == "France"


def t_clues_fit_narrow_window():
    # every type stays reachable: the row wraps on a narrow window, and scrolls inside itself on a phone; the page never scrolls sideways
    p = page(1024, 768)
    assert p.evaluate("document.documentElement.scrollWidth <= innerWidth")
    assert p.evaluate("[...document.querySelectorAll('#clues .chip')].every(c => { const r = c.getBoundingClientRect(); return r.left >= 0 && r.right <= innerWidth && r.width > 0; })")
    q = page(390, 844)
    assert q.evaluate("document.documentElement.scrollWidth <= innerWidth")
    assert q.evaluate("(() => { const c = document.getElementById('clues'); return c.scrollWidth > c.clientWidth && getComputedStyle(c).overflowX === 'auto'; })()")


def t_clue_chips_keep_their_place():
    # same window, another country: every chip sits exactly where it was
    pos = lambda p: p.evaluate("[...document.querySelectorAll('#clues .chip')].map(c => { const r = c.getBoundingClientRect(); return [Math.round(r.left), Math.round(r.top), Math.round(r.width)]; })")
    home = pos(page(1440, 900))
    for h in ("#fr", "#id", "#pl"):
        assert pos(page(1440, 900, h)) == home, h


# ---------------------------------------------------------------- B3 country page by clue
def rows(p):
    return p.evaluate("[...document.querySelectorAll('#panel section.clue')].map(s => ({ t: s.querySelector('h3').textContent, cards: s.querySelectorAll('.thumb').length, apps: [...s.querySelectorAll('a.app')].map(a => a.textContent.replace(/\\s+/g, ' ').trim()) }))")


def t_country_rows_by_clue():
    r = rows(page(1440, 900, "#pl"))
    assert [x["t"] for x in r] == ["Language", "Architecture", "Road lines", "Phone codes"], [x["t"] for x in r]      # only clues with cards; trainers sit in their own row
    assert r[0]["cards"] == 3 and all(x["cards"] and not x["apps"] for x in r), r


def t_cards_visible_without_scrolling():
    p = page(1440, 900, "#id")
    top = p.evaluate("document.querySelector('#panel .thumb').getBoundingClientRect().top"); assert top < 460, top          # was 668 before lot B; the trainers row sits above the cards
    # cards whose picture is at least half on screen (before lot B: 1). Fonts change the exact heights, so the message lists where they sit.
    tops = p.evaluate("[...document.querySelectorAll('#panel .thumb img')].map(i => Math.round(i.getBoundingClientRect().top + i.getBoundingClientRect().height / 2))")
    n = len([y for y in tops if y < 900]); assert n >= 3, f"{n} cards on screen, picture centres at {tops}"
    p.click("#panel .thumb"); p.wait_for_timeout(200)
    assert p.evaluate("document.getElementById('lightbox').classList.contains('open')")


def t_refs_and_mixups_compact():
    p = page(1440, 900, "#fr")
    assert p.evaluate("[...document.querySelectorAll('#panel .refs > a')].map(a => a.textContent.trim())") == ["Plonk It ↗", "Street View ↗", "Relief ↗"]
    assert "LearnableMeta 2" in " ".join(p.inner_text("#panel .refs").split())
    assert p.evaluate("!document.querySelector('#panel .mixline')")
    p.evaluate("TGM.confusions.seed('plate-trainer', [['PL', 'CZ', 4], ['PL', 'SK', 2]])"); p.goto(BASE + "index.html#pl"); p.reload(); p.wait_for_timeout(300)
    mix = p.evaluate("[...document.querySelectorAll('#panel .mixline .mix-c')].map(b => b.textContent.replace(/\\s+/g, ' ').trim())")
    assert mix and mix[0].endswith("Czechia ×4"), mix


def t_empty_and_trainer_only_countries():
    errs = []; p = page(1440, 900, "#ve", errors=errs)
    assert rows(p) == [] and p.inner_text("#panel .none") == "No card and no trainer for this country yet."
    p = page(1440, 900, "#fr", errors=errs); r = rows(p)
    assert r == [] and p.evaluate("document.querySelectorAll('#panel .trainers a.app').length") == 4 and p.inner_text("#panel .none").startswith("Nothing yet: ")
    assert "images\\" not in p.inner_text("#panel") and errs == []


def t_trainers_row_keeps_its_place():
    """One row of trainers at the top of the country page, same order everywhere, never inside the clue sections."""
    order = None
    js = """() => { const r = document.querySelector('#panel .trainers'), s = document.querySelector('#panel section.clue');
      return { names: [...r.querySelectorAll('a.app')].map(a => a.textContent.split('↗')[0].trim()), y: r.getBoundingClientRect().bottom,
        before: !s || !!(r.compareDocumentPosition(s) & 4), inside: document.querySelectorAll('#panel section.clue a.app').length,
        all: (window.ATLAS.apps || []).map(a => a.name.en) }; }"""
    for iso in ("ph", "fr", "pl", "id"):
        p = page(1440, 900, "#" + iso); d = p.evaluate(js)
        assert d["names"] and len(set(d["names"])) == len(d["names"]) and d["before"] and d["inside"] == 0, (iso, d)
        assert d["y"] < 420, (iso, d["y"])
        ranks = [d["all"].index(n) for n in d["names"]]; assert ranks == sorted(ranks), (iso, d["names"])
    p = page(1440, 900, "#ph/plate"); d = p.evaluate(js)
    assert d["names"] == ["Plate Trainer", "Clue Fusion"] and not p.query_selector("#panel .none"), d


def t_two_type_card_once_in_viewer():
    p = page(1440, 900, "#tr"); r = rows(p)
    assert [x["t"] for x in r if x["cards"]] == ["Plates", "Signs"], r
    p.click("#panel section.clue[data-type=plate] .thumb"); p.wait_for_timeout(200)
    assert p.evaluate("document.querySelectorAll('#strip button').length") == 0 and p.is_disabled("#lbnext")


def t_accuracy_on_trainer_buttons():
    errs = []; p = page(1440, 900, errors=errs)
    p.evaluate("""() => { const mk = (a, bc) => localStorage.setItem('tgm.stats.' + a, JSON.stringify({ app: a, v: 1, byCountry: bc }));
      mk('plate-trainer', { PL: { seen: 20, correct: 8 } }); mk('bollards', { PL: { seen: 10, correct: 7 } }); mk('duels', { PL: { seen: 10, correct: 5 } }); mk('sign-reader', { PL: { seen: 2, correct: 2 } }); }""")
    p.goto(BASE + "index.html#pl"); p.reload(); p.wait_for_timeout(300)
    acc = p.evaluate("Object.fromEntries([...document.querySelectorAll('#panel a.app')].filter(a => a.querySelector('.acc')).map(a => [a.textContent.split('↗')[0].trim(), a.querySelector('.acc').textContent.trim()]))")
    assert acc == {"Bollards": "70 %"}, acc     # Plate Trainer does not cover Poland; Sign Reader has under 3 answers; duels has no button
    assert p.inner_text("#panel .facts").endswith("52 % over 42 answers"), p.inner_text("#panel .facts")
    assert p.evaluate("!document.querySelector('#panel .stats')") and errs == []


# ---------------------------------------------------------------- B4 colour by
SEED = """() => { const mk = (a, bc) => localStorage.setItem('tgm.stats.' + a, JSON.stringify({ app: a, v: 1, byCountry: bc }));
  mk('bollards', { PL: { seen: 10, correct: 4 }, DE: { seen: 30, correct: 28 }, CZ: { seen: 2, correct: 1 } }); }"""


def fill(p, iso): return p.evaluate("i => getComputedStyle(document.querySelector(`#map path[data-iso=\"${i}\"]`)).fill", iso)


def t_colour_by_modes():
    p = page(1440, 900); p.evaluate(SEED); p.reload(); p.wait_for_timeout(300)
    assert p.get_attribute("#colourBy [data-c=coverage]", "aria-checked") == "true"
    p.click("#colourBy [data-c=accuracy]"); p.wait_for_timeout(150)
    assert fill(p, "PL") == "rgb(217, 102, 58)" and fill(p, "DE") == "rgb(63, 134, 189)", (fill(p, "PL"), fill(p, "DE"))
    assert "wfew" in cls(p, "CZ") and "url(" in fill(p, "CZ")
    assert "under 3 answers" in p.inner_text("#legend") and p.evaluate("!!document.querySelector('#panel .wlist')")
    p.click("#colourBy [data-c=frequency]"); p.wait_for_timeout(150)
    assert "f1" in cls(p, "FR") and fill(p, "FR") == "rgb(242, 201, 76)" and not any(k in cls(p, "VE").split() for k in ("f1", "f2", "f3", "f4"))
    assert "Tier 1 common" in p.inner_text("#legend")
    assert p.evaluate("localStorage.getItem('atlas.colour')") == '"frequency"'
    p.reload(); p.wait_for_timeout(300); assert p.get_attribute("#colourBy [data-c=frequency]", "aria-checked") == "true"


def t_colour_legacy_values():
    for stored, want in [({"atlas.weak": "true"}, "accuracy"), ({"atlas.colour": '"nonsense"'}, "coverage"), ({"atlas.colour": "{", "atlas.weak": "false"}, "coverage")]:
        errs = []; p = page(1440, 900, errors=errs)
        p.evaluate("o => Object.entries(o).forEach(([k, v]) => localStorage.setItem(k, v))", stored); p.reload(); p.wait_for_timeout(300)
        assert p.get_attribute(f"#colourBy [data-c={want}]", "aria-checked") == "true" and errs == [], stored


# ---------------------------------------------------------------- B5 panel widths
def ratio(p): return p.evaluate("document.getElementById('panel').getBoundingClientRect().width / document.getElementById('app').getBoundingClientRect().width")


def t_panel_three_widths():
    p = page(1440, 900, "#id"); assert ratio(p) < 0.4
    p.click("#widen"); p.wait_for_timeout(200); assert 0.44 < ratio(p) < 0.56 and p.is_visible("#map"), ratio(p)
    assert p.evaluate("document.querySelector('#panel .thumb img').getBoundingClientRect().height") >= 119
    p.click("#widen"); p.wait_for_timeout(200); assert ratio(p) > 0.9 and not p.is_visible("#map"), ratio(p)
    p.reload(); p.wait_for_timeout(300); assert ratio(p) > 0.9
    p.click("#widen"); p.wait_for_timeout(200); assert ratio(p) < 0.4
    assert p.evaluate("!document.getElementById('board') && ![...document.querySelectorAll('#panel button')].some(b => b.textContent === 'Board')")


def t_type_view_gets_room_and_keeps_map():
    p = page(1440, 900); p.click("#clues .chip:has-text('Phone codes')"); p.wait_for_timeout(200)
    assert 0.44 < ratio(p) < 0.56 and p.is_visible("#map") and title(p) == "Phone codes", (ratio(p), title(p))
    assert p.evaluate("localStorage.getItem('atlas.wide')") in (None, "0")
    assert p.evaluate("document.querySelectorAll('#panel .card').length") >= 10
    p.keyboard.press("Escape"); p.wait_for_timeout(200); assert title(p) == "Atlas" and ratio(p) < 0.4


def t_wide_legacy_value():
    p = page(1440, 900); p.evaluate("localStorage.setItem('atlas.wide', '7')"); p.goto(BASE + "index.html#id"); p.reload(); p.wait_for_timeout(300); assert ratio(p) < 0.4


def t_phone_has_no_width_button():
    p = page(390, 844, "#id"); assert not p.is_visible("#widen") and p.evaluate("document.documentElement.scrollWidth <= innerWidth")
    p.click("#menuBtn"); assert p.is_visible("#pages a:has-text('Quiz')") and p.is_visible("#darkToggle")


# ---------------------------------------------------------------- B6 pages from the search
def t_search_pages_and_compare():
    p = page(1440, 900); search(p, "compare pl cz"); r = results(p)
    assert "pgrp|Pages" in r and any("Compare Poland and Czechia" in x for x in r), r
    i = next(k for k, x in enumerate([y for y in r if y.startswith("pr|")]) if "Compare Poland and Czechia" in x)
    for _ in range(i): p.keyboard.press("ArrowDown")
    p.keyboard.press("Enter"); p.wait_for_url("**/compare.html#pl/cz")
    p = page(1440, 900); search(p, "mix"); assert any(x.startswith("pr|") and "Mix-ups" in x for x in results(p)), results(p)
    p = page(1440, 900); search(p, "quiz id"); assert any("Quiz · Indonesia" in x for x in results(p)), results(p)


# ================================================================ lot C1: one bar on the six pages
def _shell():
    import importlib
    if str(ATLAS / "tools") not in sys.path: sys.path.insert(0, str(ATLAS / "tools"))
    import shell
    return importlib.reload(shell)


def t_shell_generator_is_exact():
    sh = _shell()
    assert list(sh.PAGES) == [("index.html", "Explore"), ("daily.html", "Review"), ("games.html", "Duels"), ("confusions.html", "Mix-ups"), ("quiz.html", "Quiz")]
    tabs = sh.tabs_html("games.html")
    assert tabs.count("<a ") == 5 and tabs.count('aria-current="page"') == 1 and 'href="games.html" aria-current="page"' in tabs, tabs
    assert sh.tabs_html(None).count("aria-current") == 0 and 'href="./"' not in sh.bar_html(None)


def t_shell_idempotent_and_strict():
    sh = _shell(); import tempfile, shutil
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        for f in [p for p, _ in sh.PAGES] + list(sh.EXTRA): shutil.copy(ATLAS / f, d / f)
        assert sh.check(d) == [], sh.check(d)                              # the folder is in sync
        assert sh.apply(d, quiet=True) == []                               # so a run writes nothing
        before = (d / "quiz.html").read_bytes(); assert b"\r\n" not in before
        (d / "quiz.html").write_bytes(before.replace(b">Review</a>", b">Revue</a>", 1))   # hand edit inside a block
        assert sh.check(d) == ["quiz.html"]
        assert sh.apply(d, quiet=True) == ["quiz.html"] and (d / "quiz.html").read_bytes() == before
        broken = (d / "daily.html").read_bytes().replace(b"<!-- /tgm-shell:bar -->", b"", 1)
        (d / "daily.html").write_bytes(broken)
        (d / "quiz.html").write_bytes(before.replace(b">Review</a>", b">Revue</a>", 1))
        try:
            sh.apply(d, quiet=True); raise AssertionError("a missing marker must stop the script")
        except sh.ShellError as e:
            assert "daily.html" in str(e), str(e)
        assert b">Revue</a>" in (d / "quiz.html").read_bytes()              # nothing half-written: no page was touched
        assert sh.check(d) and "daily.html" in " ".join(sh.check(d))


SHELL_PAGES = ["index.html", "daily.html", "games.html", "confusions.html", "quiz.html", "compare.html"]
CURRENT = {"index.html": "Explore", "daily.html": "Review", "games.html": "Duels", "confusions.html": "Mix-ups", "quiz.html": "Quiz", "compare.html": None}


def t_same_tabs_on_every_page():
    ref = None
    for f in SHELL_PAGES:
        p = page(1440, 900, path=f)
        tabs = p.evaluate("[...document.querySelectorAll('.tgm-tabs a')].map(a => { const r = a.getBoundingClientRect(); return [a.textContent.trim(), a.getAttribute('href'), Math.round(r.left), Math.round(r.top), Math.round(r.width), a.getAttribute('aria-current'), getComputedStyle(a).borderBottomColor]; })")
        assert [t[0] for t in tabs] == ["Explore", "Review", "Duels", "Mix-ups", "Quiz"], (f, tabs)
        assert [t[1] for t in tabs] == ["index.html", "daily.html", "games.html", "confusions.html", "quiz.html"], f
        cur = [t for t in tabs if t[5] == "page"]
        assert [t[0] for t in cur] == ([CURRENT[f]] if CURRENT[f] else []), (f, cur)
        assert all(t[6] == "rgb(242, 201, 76)" for t in cur), f
        place = [t[2:5] for t in tabs]; ref = ref or place
        assert place == ref, f"{f}: tabs at {place}, on index.html at {ref}"
        home = p.evaluate("(() => { const h = document.querySelector('.tgm-home, #home').getBoundingClientRect(); return [Math.round(h.left), Math.round(h.top)]; })()")
        assert home[0] == 20 and abs(home[1] - 16) <= 4, (f, home)
        p.context.close()


def t_sub_pages_share_the_base_look():
    font = page(1440, 900).evaluate("getComputedStyle(document.body).fontFamily")
    for f in SHELL_PAGES[1:]:
        errs = []; p = page(1440, 900, path=f, errors=errs)
        assert p.evaluate("getComputedStyle(document.documentElement).getPropertyValue('--land').trim()") == "#2b4c60", f
        assert p.evaluate("getComputedStyle(document.body).fontFamily") == font, f
        assert p.evaluate("!document.querySelector('header a[href=\"./\"], header .right a[href$=\".html\"]')"), f"{f}: old link row still there"
        assert p.get_attribute(".tgm-home", "href") == "index.html"
        radii = p.evaluate("[...document.querySelectorAll('button, select')].filter(b => b.offsetParent).map(b => getComputedStyle(b).borderRadius)")
        assert all(r in ("4px", "0px") for r in radii), (f, radii)
        assert errs == [], (f, errs)
        p.context.close()


def t_sub_pages_fit_a_phone():
    for f in SHELL_PAGES[1:]:
        p = page(390, 844, path=f)
        assert p.evaluate("document.documentElement.scrollWidth <= innerWidth"), f
        p.evaluate("document.querySelector('.tgm-tabs a:last-child').scrollIntoView({ inline: 'end', block: 'nearest' })")
        assert p.evaluate("(() => { const r = document.querySelector('.tgm-tabs a:last-child').getBoundingClientRect(); return r.left >= 0 && r.right <= innerWidth + 1; })()"), f
        p.context.close()


def t_page_controls_survive():
    p = page(1440, 900, path="daily.html"); assert p.evaluate("!!document.querySelector('header #streak')")
    p = page(1440, 900, path="games.html"); assert p.evaluate("['link', 'reload', 'clink'].every(i => document.getElementById(i) && document.getElementById(i).closest('header'))")
    p = page(1440, 900, path="compare.html", hash="#pl/cz"); assert p.evaluate("document.getElementById('selA').value") == "PL"


def t_build_and_smoke_guard_the_shell():
    src = (ATLAS / "build.py").read_text(encoding="utf-8"); assert "shell.apply(" in src and "ShellError" in src
    sm = (ATLAS / "tools" / "smoke.py").read_text(encoding="utf-8"); assert "shell.check(" in sm and "désynchronisée" in sm


# ================================================================ lot C2: map labels, full address, author view, New
def label(p, iso):
    """[text, visible, height on screen] of a country's map label."""
    return p.evaluate("""i => { const t = document.querySelector(`#map text[data-iso="${i}"]`); if (!t) return null;
      const r = t.getBoundingClientRect(); return [t.textContent, getComputedStyle(t).display !== 'none' && r.width > 0, Math.round(r.height)]; }""", iso)


def t_labels_follow_zoom():
    p = page(1440, 900)
    for iso in ("RU", "US", "BR", "AU"):
        l = label(p, iso); assert l and l[1] and l[0] in (iso, p.evaluate("i => window.WORLD.namesEn[i]", iso)), (iso, l)
    for iso in ("LU", "SI", "MC"):
        assert not label(p, iso)[1], iso                                  # too small on the world view
    h0 = label(p, "RU")[2]
    p = page(1440, 900, "#pl"); p.wait_for_timeout(300)
    assert label(p, "PL") == ["Poland", True, label(p, "PL")[2]], label(p, "PL")
    assert label(p, "CZ")[1] and label(p, "SK")[1]
    assert 9 <= label(p, "PL")[2] <= 18 and 9 <= h0 <= 18, (h0, label(p, "PL")[2])   # same size on screen at every zoom


def t_labels_do_not_catch_clicks():
    p = page(1440, 900)
    x, y = p.evaluate("(() => { const r = document.querySelector('#map text[data-iso=\"RU\"]').getBoundingClientRect(); return [r.left + r.width / 2, r.top + r.height / 2]; })()")
    p.mouse.click(x, y); p.wait_for_timeout(250); assert title(p) == "Russia"


def t_labels_setting():
    p = page(1440, 900); p.click("#settingsBtn"); assert p.get_attribute("#labelsToggle", "aria-checked") == "true"
    p.click("#labelsToggle"); p.wait_for_timeout(150)
    assert p.evaluate("[...document.querySelectorAll('#map text[data-iso]')].every(t => t.getBoundingClientRect().width === 0)")
    p.reload(); p.wait_for_timeout(350); assert not label(p, "RU")[1] and p.evaluate("localStorage.getItem('atlas.labels')") == "false"


def hsh(p): return p.evaluate("decodeURIComponent(location.hash)")


def t_address_carries_state():
    p = page(1440, 900); p.click("#clues .chip:has-text('Phone codes')"); p.wait_for_timeout(150); assert hsh(p) == "#t/phone"
    p.click("#clues .chip.cluster"); p.wait_for_timeout(150); assert hsh(p) == "#c/cyrillic/phone", hsh(p)
    p = page(1440, 900, "#pl"); p.click("#clues .chip:has-text('Language')"); p.wait_for_timeout(150); assert hsh(p) == "#pl/language"
    p.click("#panel .thumb"); p.wait_for_timeout(250); h = hsh(p)
    assert h.startswith("#pl/language@") and len(h) > len("#pl/language@") + 3, h
    card = " ".join(p.inner_text("#lbtitle").split())
    q = page(1440, 900, h); q.wait_for_timeout(300)                       # the address alone restores everything
    assert title(q) == "Poland" and q.evaluate("document.querySelector('#clues .chip.on b').textContent") == "Language"
    assert q.evaluate("document.getElementById('lightbox').classList.contains('open')") and " ".join(q.inner_text("#lbtitle").split()) == card
    q.keyboard.press("Escape"); q.wait_for_timeout(150); assert hsh(q) == "#pl/language"
    for h, want, chip in [("#t/phone", "Phone codes", "Phone codes"), ("#c/cyrillic", "Cyrillic", "Cyrillic"), ("#c/cyrillic/language", "Cyrillic", "Language")]:
        q = page(1440, 900, h); assert title(q) == want, (h, title(q))
        assert chip in q.evaluate("[...document.querySelectorAll('#clues .chip.on b')].map(b => b.textContent)"), h


def t_address_legacy_and_garbage():
    for h, want, typ in [("#fr", "France", None), ("#pl/cz", "Poland", None), ("#t/zzz", "Atlas", None), ("#c/nope", "Atlas", None), ("#pl@zzzz", "Poland", None), ("#@zzzz", "Atlas", None), ("#pl/language/extra", "Poland", "Language")]:
        errs = []; p = page(1440, 900, h, errors=errs)
        on = p.evaluate("[...document.querySelectorAll('#clues .chip.on b')].map(b => b.textContent)")
        assert title(p) == want and on == ([typ] if typ else []) and errs == [], (h, title(p), on, errs)
        assert not p.evaluate("document.getElementById('lightbox').classList.contains('open')"), h
        p.context.close()


def t_back_keeps_the_filter():
    p = page(1440, 900, "#pl"); p.click("#clues .chip:has-text('Language')"); p.wait_for_timeout(150)
    search(p, "czechia"); p.keyboard.press("Enter"); p.wait_for_timeout(250); assert title(p) == "Czechia"
    p.go_back(); p.wait_for_timeout(250)
    assert title(p) == "Poland" and p.evaluate("[...document.querySelectorAll('#clues .chip.on b')].map(b => b.textContent)") == ["Language"]


PUBLIC = "http://atlas.test/"


def t_author_tools_switch():
    p = page(1440, 900)                                                    # localhost: author tools on by default
    assert "To fill in" in p.inner_text("#panel")
    p = page(1440, 900, "#fr"); assert p.inner_text("#panel .none").startswith("Nothing yet: ")
    p.click("#settingsBtn"); assert p.get_attribute("#authorToggle", "aria-checked") == "true"; p.click("#authorToggle"); p.wait_for_timeout(150)
    assert p.evaluate("!document.querySelector('#panel .none')") and p.evaluate("localStorage.getItem('atlas.author')") == "false"
    p.goto(BASE + "index.html"); p.reload(); p.wait_for_timeout(300); assert "To fill in" not in p.inner_text("#panel")
    p.click("#clues .chip:has-text('Phone codes')"); p.wait_for_timeout(200)
    assert p.evaluate("document.querySelectorAll('#panel .card').length") >= 10 and p.evaluate("!document.querySelector('#panel .low')")


def t_reader_view_on_a_public_site():
    errs = []; p = page(1440, 900, host=PUBLIC, errors=errs)
    assert title(p) == "Atlas" and "To fill in" not in p.inner_text("#panel")
    p.click("#settingsBtn"); assert p.get_attribute("#authorToggle", "aria-checked") == "false"
    p.click("#authorToggle"); p.wait_for_timeout(150); assert "To fill in" in p.inner_text("#panel")      # the author switches it on once, there
    p = page(1440, 900, "#ve", host=PUBLIC, errors=errs); assert p.inner_text("#panel .none") == "No card and no trainer for this country yet."
    assert errs == [], errs


def _dates(today_n=3, old="2026-01-01"):
    import datetime
    today = datetime.date.today().isoformat()
    def edit(cards):
        for k, c in enumerate(cards): c["added"] = today if k < today_n else old
    return today, edit


def new_titles(p): return p.evaluate("(() => { const s = document.querySelector('#panel section.new'); return s ? [s.querySelector('h2').textContent.trim(), s.querySelectorAll('.thumb').length] : null; })()")


def t_new_since_last_visit():
    import datetime, json
    today, edit = _dates(3)
    y = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
    p = page(1440, 900, data=edit, storage={"atlas.seen": json.dumps({"last": "2026-11-01", "now": y})})
    assert new_titles(p) == ["New since your last visit", 3], new_titles(p)
    assert json.loads(p.evaluate("localStorage.getItem('atlas.seen')")) == {"last": y, "now": today}
    p.reload(); p.wait_for_timeout(300); assert new_titles(p) == ["New since your last visit", 3]          # still there on a reload the same day
    p.click("#panel section.new .thumb"); p.wait_for_timeout(200); assert p.evaluate("document.getElementById('lightbox').classList.contains('open')")
    p = page(1440, 900, data=edit, storage={"atlas.seen": json.dumps({"last": y, "now": today})}); assert new_titles(p) == ["New since your last visit", 3]
    p = page(1440, 900, data=edit, storage={"atlas.seen": json.dumps({"last": today, "now": today})}); assert new_titles(p) is None


def t_new_on_first_visit_and_without_dates():
    today, edit = _dates(2)
    p = page(1440, 900, data=edit); assert new_titles(p) == ["Added recently", 2], new_titles(p)          # first visit: the last 14 days
    errs = []
    def strip(cards):
        for c in cards: c.pop("added", None)
    p = page(1440, 900, data=strip, errors=errs); assert new_titles(p) is None and errs == []            # data.js built before this lot
    p = page(1440, 900, data=edit, storage={"atlas.seen": "{oops"}, errors=errs); assert new_titles(p) == ["Added recently", 2] and errs == []


def t_data_has_added_dates():                 # needs data.js rebuilt by build.cmd
    p = page(1440, 900)
    assert p.evaluate("window.ATLAS.cards.every(c => /^\\d{4}-\\d\\d-\\d\\d$/.test(c.added || ''))"), "run build.cmd first"
    assert '"added"' in (ATLAS / "build.py").read_text(encoding="utf-8")


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
