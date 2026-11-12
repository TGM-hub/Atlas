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


if __name__ == "__main__":
    if "--check" in sys.argv:
        stale = check()
        print("Barre commune à jour." if not stale else "À régénérer (py tools\\shell.py) : " + ", ".join(stale))
        sys.exit(1 if stale else 0)
    try:
        changed = apply()
        print("Barre commune : rien à changer." if not changed else f"{len(changed)} page(s) mise(s) à jour.")
    except ShellError as e:
        print(e); sys.exit(1)
