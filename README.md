# GeoGuessr Atlas

🌐 [Atlas](https://tgm-hub.github.io/Atlas/)

## Installation (une fois)
1. `pip install pillow`
2. Dans le dossier Atlas : `powershell -ExecutionPolicy Bypass -File .\setup-atlas.ps1`
   Crée (et migre si besoin) l'arborescence `images\` et le raccourci `GeoGuessr Atlas.lnk`.
3. Clic droit sur `GeoGuessr Atlas.lnk` > Épingler à la barre des tâches.

## Ajouter des fiches
1. Glisse l'image dans `images\<pays>\<type>\` ; le nom du fichier devient le titre.
   - `images\BR Brazil\phone\DDD.png` : un pays
   - `images\_multi\JP+TW\phone\Japan and Taiwan.png` : plusieurs pays
   - `images\_clusters\cyrillic\language\Alphabet.png` : un cluster
   - `images\_world\bollard\Europe.png` : mondial
   - `images\JP Japan\other\Post signs.png` : ce qui ne rentre nulle part
   - deux types à la fois : dossier `bollard+pole\`
   - sous-dossier de regroupement (un seul niveau) : `images\ID Indonesia\other\Kabupaten\Java.png`, affiché en section repliable « Kabupaten »
2. `build.cmd` (ou `publish.cmd` si tu partages l'atlas).
3. F5 dans l'atlas.

Types : landscape, language, architecture, plate, bollard, pole, sign, road-lines, phone, car, soil, flag, other.
Nouveau type ou alias de recherche : `config.json`, puis relance `setup-atlas.ps1`.

## Trainers
`apps.json` liste les trainers (un repo par outil). Le build le valide et l'injecte dans `data.js` ;
l'accueil affiche ceux en `live` et `wip` (badge « en cours »), un clic ouvre un nouvel onglet.
Statuts : `live`, `wip`, `local` (pas encore en ligne, masqué), `idea` (masqué).

## Recherche
Tape au clavier n'importe quand. Pays en anglais, en français ou code ISO ; types en anglais ou en français
(« car paraguay », « voiture paraguay », « phone br », « plaque pologne »). Entrée ouvre la fiche.

## Partage (GitHub Pages)
`images\` n'est pas publié : le build en garde une copie dans `thumbs\full\`.
Supprime la ligne `images/` de `.gitignore` si tu veux aussi sauvegarder les originaux sur GitHub.

## Relief
`relief.webp` : ombrage du relief (Natural Earth, domaine public) reprojeté dans la projection de `map.js`, affiché par-dessus les pays. Opacité réglable dans `index.html` (`#map .relief`).
