"""Checks of the Atlas strip and colours in the trainers. Run: py tools\\test_trainers.py [test names…]
The trainers are the folders next to the Atlas under the user's home (or SMOKE_HOME), as in smoke.py.
Needs Playwright. Browser: Edge, or SMOKE_BROWSER=chromium. Exit code 0 when every test passes."""
import os, shutil, socket, sys, tempfile, threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ATLAS = Path(__file__).resolve().parent.parent
HOME = Path(os.environ.get("SMOKE_HOME") or Path.home())
sys.path.insert(0, str(ATLAS / "tools"))
import shell  # noqa: E402

BROWSER = None
BASE = None
SITE = "https://tgm-hub.github.io/Atlas/"


class Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *a): pass


class Server(ThreadingHTTPServer):
    def handle_error(self, request, client_address):      # a page closed in the middle of a download is not an error
        if not isinstance(sys.exc_info()[1], ConnectionError):
            super().handle_error(request, client_address)


def page(repo, width=1440, height=900, hash="", errors=None):
    ctx = BROWSER.new_context(viewport={"width": width, "height": height}, service_workers="block")
    ctx.route(lambda url: not url.startswith(BASE), lambda r: r.fulfill(status=200, content_type="text/html", body=""))   # never leave the machine
    p = ctx.new_page(); p.set_default_timeout(5000)
    if errors is not None:
        p.on("pageerror", lambda e: errors.append(str(e)))
    p.goto(BASE + repo + "/index.html" + hash, wait_until="load"); p.wait_for_timeout(900)
    return p


CONTRAST = """el => { const lum = c => { const v = c.match(/[\\d.]+/g).map(Number).slice(0, 3).map(x => { x /= 255; return x <= .03928 ? x / 12.92 : Math.pow((x + .055) / 1.055, 2.4); }); return .2126 * v[0] + .7152 * v[1] + .0722 * v[2]; };
  let b = el, bg = 'rgba(0, 0, 0, 0)'; while (b && /rgba\\(.*, 0\\)|transparent/.test(bg = getComputedStyle(b).backgroundColor)) b = b.parentElement;
  const a = lum(getComputedStyle(el).color), c = lum(b ? bg : 'rgb(18, 40, 58)'); return (Math.max(a, c) + .05) / (Math.min(a, c) + .05); }"""


def strip(p):
    return p.evaluate("""() => ({ links: [...document.querySelectorAll('.tgm-nav > a')].map(a => { const r = a.getBoundingClientRect(); return [a.getAttribute('aria-label'), Math.round(r.width), Math.round(r.height), !!a.querySelector('svg')]; }),
      text: document.querySelector('.tgm-nav > a') ? [...document.querySelectorAll('.tgm-nav > a, .tgm-maps > summary')].map(e => e.textContent.trim()).join('') : null,
      maps: !!document.querySelector('.tgm-nav .tgm-maps > summary svg'), items: document.querySelectorAll('.tgm-pop li').length })""")


def press(p, label):
    """Press the pointer on a strip link (without leaving the page) and read where it now points."""
    p.dispatch_event(f".tgm-nav > a[aria-label='{label}']", "pointerdown")
    return p.get_attribute(f".tgm-nav > a[aria-label='{label}']", "href")


def check_strip(repo, n_maps):
    s = strip(page(repo))
    assert [l[0] for l in s["links"]] == ["Atlas", "Daily review", "Mix-ups"], s
    assert all(l[1:] == [28, 28, True] for l in s["links"]) and s["maps"], s
    assert s["text"] == "" and s["items"] == n_maps, s                       # drawn icons only; the list of maps is the trainer's own


# ---------------------------------------------------------------- generator (no browser)
def t_generator_links_are_exact():
    h = shell.trainer_links_html()
    assert h.count("<a ") == 3 and h.count("<svg") == 3, h
    order = [h.index(f'aria-label="{l}"') for l in ("Atlas", "Daily review", "Mix-ups")]; assert order == sorted(order)
    assert SITE + '"' in h and SITE + 'daily.html"' in h and SITE + 'confusions.html"' in h and 'target="gg-daily"' in h
    for bad in "⌂⏱🎯⇄": assert bad not in h + shell.trainer_maps_html() + shell.trainer_css()
    assert set(shell.TRAINERS) >= {"phone-codes", "bollards-trainer"}


def t_generator_is_idempotent_and_strict():
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        for repo in ("phone-codes", "bollards-trainer"):
            (d / repo).mkdir(); shutil.copy(HOME / repo / "index.html", d / repo / "index.html")
        assert shell.check_trainers(d) == [], shell.check_trainers(d)          # in sync
        assert shell.apply_trainers(d, quiet=True) == []
        f = d / "phone-codes" / "index.html"; before = f.read_bytes()
        f.write_bytes(before.replace(b'aria-label="Mix-ups"', b'aria-label="Mixups"', 1))
        assert shell.check_trainers(d) == ["phone-codes/index.html"]
        assert shell.apply_trainers(d, quiet=True) == ["phone-codes/index.html"] and f.read_bytes() == before
        other = d / "bollards-trainer" / "index.html"; ob = other.read_bytes()
        other.write_bytes(ob.replace(b'aria-label="Atlas"', b'aria-label="Atlass"', 1)); stale = other.read_bytes()
        f.write_bytes(before.replace(b"<!-- /tgm-shell:links -->", b"", 1))
        try:
            shell.apply_trainers(d, quiet=True); raise AssertionError("a missing marker must stop the script")
        except shell.ShellError as e:
            assert "phone-codes/index.html" in str(e), str(e)
        assert other.read_bytes() == stale                                    # nothing written anywhere
        f.write_bytes(before); shutil.rmtree(d / "bollards-trainer")
        assert shell.apply_trainers(d, quiet=True) == [] and shell.check_trainers(d) == []   # a missing repo is skipped


def t_build_and_smoke_guard_the_trainers():
    assert "shell.apply_trainers(" in (ATLAS / "build.py").read_text(encoding="utf-8")
    sm = (ATLAS / "tools" / "smoke.py").read_text(encoding="utf-8"); assert "shell.check_trainers(" in sm and "bande Atlas désynchronisée" in sm


# ---------------------------------------------------------------- phone-codes
def t_phone_codes_strip():
    check_strip("phone-codes", 8)


def t_phone_codes_links_follow_the_country():
    errs = []; p = page("phone-codes", hash="#br", errors=errs)
    assert press(p, "Atlas") == SITE + "#br" and press(p, "Mix-ups") == SITE + "confusions.html#br"
    assert p.get_attribute(".tgm-nav > a[aria-label='Daily review']", "href") == SITE + "daily.html"
    p.select_option("#country", "JP"); p.wait_for_timeout(700); assert press(p, "Atlas") == SITE + "#jp"
    p.evaluate("window.__keep = window.C; try { C = null; } catch (e) {}"); assert press(p, "Atlas") in (SITE, SITE + "#jp")
    assert errs == [], errs


def t_phone_codes_colours():
    p = page("phone-codes", hash="#fr")
    assert p.evaluate("getComputedStyle(document.body).backgroundColor") == "rgb(18, 40, 58)"
    assert p.evaluate("getComputedStyle(document.documentElement).getPropertyValue('--amber').trim().toLowerCase()") == "#f2c94c"
    low = p.evaluate("(f => [...document.querySelectorAll('#rail button, #rail select, #rail .stat, .seg button, .act, #side *')].filter(e => e.offsetParent && e.childElementCount === 0 && e.textContent.trim()).map(e => [e.tagName + '.' + e.className, +(eval(f))(e).toFixed(2)]).filter(x => x[1] < 4.5))(%r)" % CONTRAST)
    assert low == [], low[:8]


def t_phone_codes_fits_a_phone():
    p = page("phone-codes", 390, 844, "#br")
    assert p.evaluate("document.documentElement.scrollWidth <= innerWidth")
    assert p.evaluate("(() => { const r = document.getElementById('country').getBoundingClientRect(); return r.left >= 0 && r.right <= innerWidth && r.width > 60; })()")
    p.click(".tgm-maps > summary"); p.wait_for_timeout(150)
    assert p.evaluate("(() => { const r = document.querySelector('.tgm-pop').getBoundingClientRect(); return r.width > 150 && r.left >= 0 && r.right <= innerWidth; })()")


# ---------------------------------------------------------------- bollards
def t_bollards_strip():
    check_strip("bollards-trainer", 6)


def t_bollards_links_follow_the_country():
    errs = []; p = page("bollards-trainer", errors=errs)
    assert press(p, "Atlas") == SITE and press(p, "Mix-ups") == SITE + "confusions.html"       # no country yet
    p = page("bollards-trainer", hash="#fr", errors=errs)
    assert press(p, "Atlas") == SITE + "#fr" and press(p, "Mix-ups") == SITE + "confusions.html#fr"
    p = page("bollards-trainer", hash="#stats", errors=errs); assert press(p, "Atlas") == SITE   # a hash that is not a country
    assert errs == [], errs


def t_bollards_colours():
    p = page("bollards-trainer")
    assert p.evaluate("getComputedStyle(document.body).backgroundColor") == "rgb(18, 40, 58)"
    assert p.evaluate("getComputedStyle(document.documentElement).getPropertyValue('--accent').trim().toLowerCase()") == "#f2c94c"
    def on_accent():
        return p.evaluate("(f => [...document.querySelectorAll('button, a, span, b, div')].filter(e => e.offsetParent && getComputedStyle(e).backgroundColor === 'rgb(242, 201, 76)' && e.textContent.trim()).map(e => [e.textContent.trim().slice(0, 20), +(eval(f))(e).toFixed(2)]))(%r)" % CONTRAST)
    seen = on_accent(); assert seen and all(c >= 4.5 for _, c in seen), seen
    p.click("#mStats"); p.wait_for_timeout(300); assert all(c >= 4.5 for _, c in on_accent()), on_accent()
    p.click("#mSet"); p.wait_for_timeout(300); assert all(c >= 4.5 for _, c in on_accent()), on_accent()
    low = p.evaluate("(f => [...document.querySelectorAll('header *, .choice')].filter(e => e.offsetParent && e.childElementCount === 0 && e.textContent.trim()).map(e => [e.tagName + '.' + e.className, +(eval(f))(e).toFixed(2)]).filter(x => x[1] < 4.5))(%r)" % CONTRAST)
    assert low == [], low[:8]


def t_bollards_fits_a_phone():
    p = page("bollards-trainer", 390, 844)
    assert p.evaluate("document.documentElement.scrollWidth <= innerWidth")
    assert p.evaluate("(() => { const r = document.getElementById('mSet').getBoundingClientRect(); return r.left >= 0 && r.right <= innerWidth; })()")
    p.click(".tgm-maps > summary"); p.wait_for_timeout(150)
    assert p.evaluate("(() => { const r = document.querySelector('.tgm-pop').getBoundingClientRect(); return r.width > 150 && r.left >= 0 && r.right <= innerWidth; })()")


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
    s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
    httpd = Server(("127.0.0.1", port), partial(Quiet, directory=str(HOME)))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    BASE = f"http://127.0.0.1:{port}/"
    failed = 0
    with sync_playwright() as pw:
        kind = os.environ.get("SMOKE_BROWSER", "msedge")
        BROWSER = pw.chromium.launch(**({} if kind == "chromium" else {"channel": kind}))
        for n in names:
            try:
                tests[n](); print("PASS", n)
            except Exception as e:
                import traceback
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
