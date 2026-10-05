"""Télécharge les images d'une page pays Plonk It dans _private_cache/plonkit/<pays>/ (usage perso, jamais publié).
Lent et poli : 1 page + 1 image toutes les 2 s, cache local (ne retélécharge jamais un fichier déjà présent).
Usage (PowerShell, dossier Atlas) :  python tools\\plonkit_fetch.py philippines
Option : --all pour toutes les images (par défaut : sections régionales, fichiers commençant par 2_ ou 3_, + cartes)."""
import re, sys, time, urllib.request
from pathlib import Path

UA = "Mozilla/5.0 (personal study cache; GeoGuessr Atlas)"
ROOT = Path(__file__).resolve().parent.parent / "_private_cache" / "plonkit"

# Repli si la page est rendue en JavaScript (noms relevés dans le navigateur le 2026-10-03)
KNOWN = {"philippines": "2_blackwhiteboxes.png 2_tuktukmap.jpeg provinces.png 2_areacodes.png 2_licenceplates.png 2_luzonmountain.png 2_corn.png 2_oilpalms.png 2_sugarcane.png 2_pineapple.png 2_banana.png 2_mindanaotree.png 2_diamondpatternhouse.png 2_palawanpatternhouse.png 2_baguioconcreteguardrail.png 2_bicolguardrail.png 2_chilepole.png 2_manilapoletop.png 2_zamboangapole.png 2_islam.png 2_mountaindew.png 2_cambocar.png 3_chocolatehills.png 3_arayatvolcano.png 3_mayonvolcano.png 3_marawiruins.png 3_bataandeathmarchstone.png 3_trans-palawanhighway.png 3_siquijorlamp.png 3_marinduqueromansoldier.png".split()}

def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()

def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args: sys.exit("Usage : python tools\\plonkit_fetch.py <pays> [--all]")
    country = args[0].lower()
    out = ROOT / country; out.mkdir(parents=True, exist_ok=True)
    page = out / "_page.html"
    if not page.exists():
        page.write_bytes(get(f"https://www.plonkit.net/{country}")); time.sleep(2)
    html = page.read_text(encoding="utf-8", errors="ignore")
    files = sorted(set(re.findall(rf"/images/resize/\d+/\d+/{re.escape(country)}/([^\"'?\s)]+)", html)))
    if not files and country in KNOWN:
        files = KNOWN[country]; print("(page rendue en JavaScript : liste connue utilisée)")
    if "--all" not in sys.argv:
        files = [f for f in files if re.match(r"(2_|3_|provinces|regions|map)", f)]
    print(f"{len(files)} image(s) à vérifier pour {country}")
    for f in files:
        dst = out / f
        if dst.exists(): continue
        try:
            dst.write_bytes(get(f"https://www.plonkit.net/images/resize/900/80/{country}/{f}"))
            print("  +", f)
        except Exception as e:
            print("  !", f, e)
        time.sleep(2)
    print("Terminé :", out)

if __name__ == "__main__":
    main()
