"""Barre et styles communs des pages de l'Atlas : un seul endroit pour les changer.

Chaque page reste un fichier autonome (elle marche en file://) : ce script y écrit des blocs
entre marqueurs, comme pwa.py le fait pour le bloc tgm-pwa.

  <!-- tgm-shell:css -->  … <!-- /tgm-shell:css -->    couleurs, police, barre, formes de base
  <!-- tgm-shell:bar -->  … <!-- /tgm-shell:bar -->    la barre entière (Review, Duels, Mix-ups, Compare, Quiz)
  <!-- tgm-shell:tabs --> … <!-- /tgm-shell:tabs -->   les onglets seuls (index.html, qui a sa propre barre)

Usage :
  py tools\\shell.py            réécrit les blocs des pages qui ont changé
  py tools\\shell.py --check    n'écrit rien ; code 1 si une page n'est plus à jour

build.py lance apply() à chaque build ; smoke.py lance check(). Ne jamais modifier un bloc à la main.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Onglets, dans l'ordre. Compare n'est pas un onglet : on y arrive depuis une fiche pays ou la recherche.
PAGES = [("index.html", "Explore"), ("daily.html", "Review"), ("games.html", "Duels"), ("confusions.html", "Mix-ups"), ("quiz.html", "Quiz")]
EXTRA = ["compare.html"]
TITLES = {
    "index.html": "Map, countries and cards",
    "daily.html": "Daily review (2 × 30 min)",
    "games.html": "Your Duels and Team Duels, place by place",
    "confusions.html": "Countries you mix up, across trainers",
    "quiz.html": "Recall the cards, spaced repetition",
}

CSS = """<style id="tgm-shell">
  /* Généré par tools/shell.py, ne pas modifier à la main */
  :root {
    --ocean: #12283a; --panel: #0e2130; --land: #2b4c60; --line: #3b5a6d;
    --ink: #e6eef2; --muted: #8ea6b4; --sign: #f2c94c;
    --font: Bahnschrift, "DIN Alternate", "DIN 2014", "Roboto Condensed", "Arial Narrow", system-ui, sans-serif;
  }
  .tgm-bar { display: flex; align-items: center; gap: 10px; min-height: 34px; margin: 0 -16px 14px; padding: 0 20px; font-family: var(--font); }
  .tgm-home { padding: 2px 10px 2px 0; font-size: 22px; font-weight: 700; letter-spacing: -.01em; line-height: normal; color: var(--ink); text-decoration: none; }
  .tgm-tabs { display: flex; gap: 2px; }
  .tgm-bar .tgm-tabs { margin-left: auto; }
  .tgm-tabs a { padding: 7px 11px 5px; font-size: 16px; font-weight: 600; line-height: normal; color: var(--muted); text-decoration: none; border-bottom: 2px solid transparent; white-space: nowrap; }
  .tgm-tabs a:hover { color: var(--ink); }
  .tgm-tabs a[aria-current] { color: var(--ink); border-bottom-color: var(--sign); }
  @media (max-width: 700px) {
    .tgm-bar { flex-wrap: wrap; gap: 2px 6px; margin-bottom: 10px; padding: 0 16px; }
    .tgm-home { font-size: 19px; }
    .tgm-bar .tgm-tabs { flex: 1 1 100%; margin-left: 0; justify-content: space-between; overflow-x: auto; scrollbar-width: none; }
    .tgm-bar .tgm-tabs::-webkit-scrollbar { display: none; }
    .tgm-bar .tgm-tabs a { padding: 6px 6px 4px; font-size: 15px; }
  }
  /* Formes communes : 4 px pour les contrôles, 6 px pour les surfaces */
  .wrap button, .wrap select, .wrap input, .wrap textarea { border-radius: 4px; }
  .wrap .card, .wrap section, .wrap #card, .wrap .bar { border-radius: 6px; }
</style>"""


class ShellError(Exception):
    def __init__(self, page, reason):
        super().__init__(f"{page} : {reason} (blocs tgm-shell ; voir tools/shell.py)")
        self.page = page


def tabs_html(current):
    """Les cinq onglets, dans l'ordre ; aria-current sur celui de la page `current` (None : aucun)."""
    cur = ' aria-current="page"'
    return "".join(f'<a href="{f}"{cur if f == current else ""} title="{TITLES[f]}">{label}</a>' for f, label in PAGES)


def bar_html(current):
    return ('<nav class="tgm-bar" aria-label="Atlas pages"><a class="tgm-home" href="index.html" title="Back to the map">Atlas</a>'
            f'<span class="tgm-tabs">{tabs_html(current)}</span></nav>')


def css_text():
    return CSS


def _block(page, text, name, content):
    a, b = f"<!-- tgm-shell:{name} -->", f"<!-- /tgm-shell:{name} -->"
    if text.count(a) != 1 or text.count(b) != 1:
        raise ShellError(page, f"marqueur « {name} » absent ou en double")
    i, j = text.index(a), text.index(b)
    if j < i:
        raise ShellError(page, f"marqueurs « {name} » dans le désordre")
    return text[:i + len(a)] + content + text[j:]


def render(page, text):
    """Le texte de la page avec ses blocs à jour. ShellError si un marqueur manque."""
    text = _block(page, text, "css", "\n" + css_text() + "\n")
    if page == "index.html":
        return _block(page, text, "tabs", tabs_html(page))
    return _block(page, text, "bar", "\n" + bar_html(page if page in dict(PAGES) else None) + "\n")


def _plan(root):
    out = {}
    for page in [f for f, _ in PAGES] + EXTRA:
        path = Path(root) / page
        if not path.exists():
            raise ShellError(page, "page absente")
        old = path.read_bytes().decode("utf-8")
        new = render(page, old)
        if new != old:
            out[page] = new
    return out


def check(root=ROOT):
    """Pages qui ne sont plus à jour (rien n'est écrit). Une page sans marqueur compte, avec la raison."""
    out = []
    for page in [f for f, _ in PAGES] + EXTRA:
        try:
            path = Path(root) / page
            old = path.read_bytes().decode("utf-8")
            if render(page, old) != old:
                out.append(page)
        except (ShellError, OSError) as e:
            out.append(f"{page} ({e})")
    return out


def apply(root=ROOT, quiet=False):
    """Réécrit les pages qui ont changé ; tout est calculé avant la première écriture."""
    plan = _plan(root)
    for page, new in plan.items():
        (Path(root) / page).write_bytes(new.encode("utf-8"))      # octets : les fins de ligne LF restent LF
        quiet or print(f"  barre commune mise à jour : {page}")
    return list(plan)


# ============================================================ trainers (un repo par outil, à côté de l'Atlas)
# Dans chaque trainer, la bande de liens vers l'Atlas est générée ici ; le trainer reste une page autonome.
#   <!-- tgm-shell:css -->   styles de la bande et de la liste des maps
#   <!-- tgm-shell:links --> les trois liens (Atlas, Review, Mix-ups)
#   <!-- tgm-shell:maps -->  l'icône du bouton « maps LearnableMeta » (la liste elle-même appartient au trainer)
#   <!-- tgm-shell:js -->    « Atlas » et « Mix-ups » visent le pays en cours ; la liste des maps reste dans la fenêtre
# "iso" : expression JavaScript qui donne le code du pays en cours dans ce trainer (ou rien).
import os
import re

HOME = Path(os.environ.get("SMOKE_HOME") or Path.home())
SITE = "https://tgm-hub.github.io/Atlas/"
HASH_ISO = "(location.hash.match(/^#([a-z]{2})$/i) || [])[1]"
HASH_ANY = "(location.hash.match(/^#(?:explore\\/|r-)?([a-z]{2})$/i) || [])[1]"      # #fr, #explore/fr, #r-us
TRAINERS = {
    "phone-codes": {"files": ["index.html"], "iso": "typeof C !== 'undefined' && C && C.iso"},
    "bollards-trainer": {"files": ["index.html"], "iso": HASH_ISO},
    "city-placer": {"files": ["index.html"], "iso": HASH_ANY},
    "plate-trainer": {"files": ["index.html"], "iso": HASH_ANY},
    "script-identifier-geoguessr": {"files": ["index.html"], "iso": HASH_ANY},
    "indonesia-kabupaten": {"files": ["src/template.html", "index.html"], "iso": "'id'"},      # index.html est construit depuis le gabarit
    "vietnam-province-guesser": {"files": ["index.html"], "iso": "'vn'"},
    "clue-fusion": {"files": ["index.html"], "iso": HASH_ANY},
    "russian-pannels-learning": {"files": ["index.html"], "iso": HASH_ANY},
}

_SVG = '<svg viewBox="0 0 16 16" width="15" height="15" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">{}</svg>'
ICONS = {
    "atlas": _SVG.format('<circle cx="8" cy="8" r="6"/><path d="M2 8h12M8 2c-2 2-2 10 0 12M8 2c2 2 2 10 0 12"/>'),
    "review": _SVG.format('<circle cx="8" cy="8.5" r="5.5"/><path d="M8 5.5v3l2 1.5M6.5 1.5h3"/>'),
    "mix": _SVG.format('<path d="M2 5h11l-2.5-2.5M14 11H3l2.5 2.5"/>'),
    "maps": _SVG.format('<circle cx="8" cy="8" r="6"/><circle cx="8" cy="8" r="2.2"/><path d="M8 1v2.5M8 12.5V15M1 8h2.5M12.5 8H15"/>'),
}

TRAINER_CSS = """<style id="tgm-shell">
/* Généré par Atlas/tools/shell.py, ne pas modifier à la main */
.tgm-nav{display:inline-flex;gap:4px;align-items:center;margin-right:6px;flex:none}
.tgm-nav>a,.tgm-maps>summary{display:inline-grid;place-items:center;box-sizing:border-box;width:28px;height:28px;padding:0;border-radius:4px;border:1px solid currentColor;opacity:.55;color:inherit;text-decoration:none;cursor:pointer;line-height:1}
.tgm-nav>a:hover,.tgm-nav>a:focus-visible,.tgm-maps[open]>summary,.tgm-maps>summary:hover,.tgm-maps>summary:focus-visible{opacity:1}
.tgm-nav svg{display:block}
.tgm-maps{position:relative;display:inline-block}
.tgm-maps>summary{list-style:none}
.tgm-maps>summary::-webkit-details-marker{display:none}
.tgm-pop{position:absolute;top:34px;left:0;z-index:9999;box-sizing:border-box;width:min(360px,calc(100vw - 24px));background:#0e2130;color:#e6eef2;border:1px solid #3b5a6d;border-radius:6px;padding:10px 12px;box-shadow:0 8px 24px #0006;font:13px/1.35 system-ui,-apple-system,"Segoe UI",sans-serif;text-align:left;white-space:normal}
.tgm-maps:not([open])>.tgm-pop{display:none}
.tgm-pop b{display:block;font-size:13px;margin-bottom:6px}
.tgm-pop a{display:inline;width:auto;height:auto;border:0;opacity:1;color:#e6eef2;text-decoration:none}
.tgm-pop a:hover{color:#f2c94c}
.tgm-pop ul{list-style:none;margin:0;padding:0}
.tgm-pop li{display:flex;gap:8px;align-items:baseline;margin:4px 0}
.tgm-pop .lv{flex:none;width:16px;text-align:center;font-size:11px;border:1px solid #3b5a6d;border-radius:3px;color:#8ea6b4}
.tgm-pop .ml{margin-left:auto;flex:none;color:#8ea6b4;font-size:12px}
</style>"""


def trainer_css():
    return TRAINER_CSS


def trainer_links_html():
    """Atlas, Review, Mix-ups : dans cet ordre, en icônes dessinées. data-atlas = page de l'Atlas à compléter par #pays."""
    return (f'<a data-atlas="" href="{SITE}" aria-label="Atlas" title="Atlas: the page of this country">{ICONS["atlas"]}</a>'
            f'<a href="{SITE}daily.html" target="gg-daily" aria-label="Daily review" title="Daily review">{ICONS["review"]}</a>'
            f'<a data-atlas="confusions.html" href="{SITE}confusions.html" aria-label="Mix-ups" title="Mix-ups: countries you take for one another">{ICONS["mix"]}</a>')


def trainer_maps_html():
    return ICONS["maps"]


def trainer_js(iso_expr):
    return ("<script>/* Généré par Atlas/tools/shell.py */(function(){var B='" + SITE + "',nav=document.querySelector('.tgm-nav');if(!nav)return;"
            "function iso(){try{var v=(" + iso_expr + ");return typeof v==='string'&&/^[a-z]{2}$/i.test(v)?v.toLowerCase():''}catch(e){return ''}}"
            "function aim(){var i=iso();nav.querySelectorAll('a[data-atlas]').forEach(function(a){a.href=B+a.getAttribute('data-atlas')+(i?'#'+i:'')})}"
            "['pointerdown','mouseenter','focusin','keydown'].forEach(function(e){nav.addEventListener(e,aim,true)});"
            "var d=nav.querySelector('.tgm-maps'),p=d&&d.querySelector('.tgm-pop');"
            "if(p)d.addEventListener('toggle',function(){p.style.left='0px';if(!d.open)return;var r=p.getBoundingClientRect(),w=document.documentElement.clientWidth,x=0;"
            "if(r.right>w-8)x=w-8-r.right;if(r.left+x<8)x=8-r.left;p.style.left=x+'px'})})();</script>")


def adopt_trainer(text):
    """Une page de trainer à l'ancienne (liens emoji, styles recopiés) reçoit les marqueurs. Sans effet si elle les a déjà."""
    if "<!-- tgm-shell:links -->" in text:
        return text
    text = re.sub(r"[ \t]*\.tgm-(?:nav|maps|pop)[^{}\n]*\{[^{}]*\}\n?", "", text)
    m = re.search(r'(<span class="tgm-nav">)((?:<a\b[^>]*>[^<]*</a>)+)', text)
    if not m or "</head>" not in text or "</body>" not in text:
        raise ShellError("trainer", "bande .tgm-nav introuvable : page non reconnue")
    text = text[:m.start(2)] + "<!-- tgm-shell:links --><!-- /tgm-shell:links -->" + text[m.end(2):]
    text = re.sub(r'(<details class="tgm-maps"><summary[^>]*>)[^<]*(</summary>)', r"\1<!-- tgm-shell:maps --><!-- /tgm-shell:maps -->\2", text, count=1)
    text = text.replace("</head>", "<!-- tgm-shell:css --><!-- /tgm-shell:css -->\n</head>", 1)
    i = text.rindex("</body>")
    return text[:i] + "<!-- tgm-shell:js --><!-- /tgm-shell:js -->\n" + text[i:]


def render_trainer(name, file, text):
    where = f"{name}/{file}"
    text = _block(where, text, "css", "\n" + trainer_css() + "\n")
    text = _block(where, text, "links", trainer_links_html())
    if "<!-- tgm-shell:maps -->" in text:                 # un trainer sans liste de maps n'a pas ce bloc
        text = _block(where, text, "maps", trainer_maps_html())
    return _block(where, text, "js", "\n" + trainer_js(TRAINERS[name]["iso"]) + "\n")


def _plan_trainers(home, strict=True):
    out, stale = {}, []
    for name, conf in TRAINERS.items():
        for file in conf["files"]:
            path = Path(home) / name / file
            if not path.exists():                          # repo absent sur cette machine : ignoré, comme tgm_core.py
                continue
            where = f"{name}/{file}"
            try:
                old = path.read_bytes().decode("utf-8")
                new = render_trainer(name, file, old)
                if new != old:
                    out[where] = (path, new)
            except ShellError as e:
                if strict:
                    raise
                stale.append(f"{where} ({e})")
    return out, stale


def check_trainers(home=None, only=None):
    """Fichiers de trainers qui ne sont plus à jour (rien n'est écrit). `only` : un seul repo."""
    plan, stale = _plan_trainers(home or HOME, strict=False)
    names = list(plan) + stale
    return [n for n in names if not only or n.startswith(only + "/")]


def apply_trainers(home=None, quiet=False):
    """Réécrit la bande dans les trainers présents ; tout est calculé avant la première écriture."""
    plan, _ = _plan_trainers(home or HOME)
    for where, (path, new) in plan.items():
        path.write_bytes(new.encode("utf-8"))
        quiet or print(f"  bande Atlas mise à jour : {where}")
    return list(plan)


if __name__ == "__main__":
    if "--check" in sys.argv:
        stale = check() + check_trainers()
        print("Barre commune et bandes des trainers à jour." if not stale else "À régénérer (py tools\\shell.py) : " + ", ".join(stale))
        sys.exit(1 if stale else 0)
    try:
        changed = apply() + apply_trainers()
        print("Barre commune et trainers : rien à changer." if not changed else f"{len(changed)} fichier(s) mis à jour.")
    except ShellError as e:
        print(e); sys.exit(1)
