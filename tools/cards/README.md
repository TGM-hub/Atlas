# Générateur de fiches Atlas

Fiches cartographiques générées (style Atlas, sombre) : `turkey.py` (codes de provinces), `south_asia.py` (écritures Inde/Bangladesh/Sri Lanka), `make_relief.py` (relief.webp de la carte d'accueil).

## Dépendances (à placer dans le dossier parent `..`, hors repo)
- `ne50_admin0.geojson`, `ne10_admin1.geojson` : https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/
- `bm/shadedrelief.jpg` : extrait du paquet pip `basemap-data` (Natural Earth, domaine public)
- `fonts/` : `npm pack @fontsource/<police>` (barlow, barlow-condensed, noto-sans-*)
- Python : pillow, numpy, scipy, shapely, playwright (Chromium)

## Règle d'exactitude
Chaque fiche recoupe au moins deux sources (Wikipedia + Plonk It), et le script vérifie les codes contre les géométries Natural Earth (assert).
