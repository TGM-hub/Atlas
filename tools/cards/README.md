# Générateur de fiches Atlas

Fiches cartographiques générées (style Atlas, sombre) : `turkey.py` (codes de provinces), `south_asia.py` (écritures Inde/Bangladesh/Sri Lanka), `indonesia.py` (toits), `vietnam_provinces.py` (63 provinces par région), `indonesia_admin.py` (38 provinces + zones de plaques), `make_relief.py` (relief.webp de la carte d'accueil), `script_groups.py` + `script_groups_data.py` (écritures par groupe : cyrillique, slaves latins + baltes, nordiques, thaï·lao·khmer ; `python script_groups.py [clé]`, PNG dans `../scripts/`, chemin de rangement affiché).

Polices de `script_groups.py` : `fonts/<paquet>/files/` tel que sorti de `npm pack @fontsource/<paquet>` (barlow, barlow-condensed, noto-sans, noto-sans-thai, noto-sans-lao, noto-sans-khmer).

`data/` : géométries extraites des trainers (`vn_provinces.json` depuis vietnam-province-guesser, `id_admin.json` depuis indonesia-kabupaten), données publiques uniquement.

## Dépendances (à placer dans le dossier parent `..`, hors repo)
- `ne50_admin0.geojson`, `ne10_admin1.geojson` : https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/
- `bm/shadedrelief.jpg` : extrait du paquet pip `basemap-data` (Natural Earth, domaine public)
- `fonts/` : `npm pack @fontsource/<police>` (barlow, barlow-condensed, noto-sans-* ; sous-ensembles vietnamese inclus dans les paquets barlow)
- Python : pillow, numpy, scipy, shapely, playwright (Chromium)

## Règle d'exactitude
Chaque fiche recoupe au moins deux sources (Wikipedia + Plonk It), et le script vérifie les codes contre les géométries Natural Earth (assert).
