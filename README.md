# GeoGuessr Atlas

🌐 [Atlas](https://tgm-hub.github.io/Atlas/)

## Installation (une fois)
1. `pip install pillow`
2. Dans le dossier Atlas : `powershell -ExecutionPolicy Bypass -File .\setup-atlas.ps1`
   Crée (et migre si besoin) l'arborescence `images\` et le raccourci `GeoGuessr Atlas.lnk`.
3. Clic droit sur `GeoGuessr Atlas.lnk` > Épingler à la barre des tâches.

## Ajouter des fiches, version rapide : _inbox
Dépose les images dans `_inbox\` avec un nom libre, puis double-clic sur `inbox.cmd` : il range chaque image
au bon endroit, nettoie le titre et relance le build.
- `phone br Indicatifs DDD.png` → `images\BR Brazil\phone\Indicatifs DDD.png`
- `language japon taiwan kana.png` → `images\_multi\JP+TW\language\Kana.png`
- `cyrillique language alphabet.png` → cluster ; `monde bollard Europe.png` → `_world`
- `other id [Kabupaten] Java.png` → sous-dossier « Kabupaten » ; `… (local).png` → fiche locale, jamais publiée
- Pays en français, en anglais ou code ISO (en MAJUSCULES s'il ressemble à un mot : DE, ES, IT…) ;
  types et clusters avec les alias de `config.json`. Le reste du nom devient le titre (« final », « updated »,
  « darkmode », « v5 »… sont retirés).
- Pays ou type introuvable : le script pose la question. `inbox.cmd --dry-run` montre sans rien déplacer.

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

## Titres des fiches
Le titre vient du nom du fichier, nettoyé au build : tirets et « _ » remplacés, bruit retiré (« final »,
« updated », « darkmode », « nobg », « v2 », numéros sauf les années), mots collés séparés (« licenceplates »),
et nom du pays retiré en début ou fin quand la fiche ne concerne qu'un pays (« Spain-road-prefixes » → « Road prefixes »).
Pour forcer un titre : `titles.json`, par exemple
`{"ES Spain/phone/Spain-telephone-codes  281 29 darkmode.png": "Indicatifs par province", "us stateflags v2": "Drapeaux des États"}`
(clé = chemin sous `images\`, ou simplement le nom du fichier sans extension).

## Trainers
`apps.json` liste les trainers (un repo par outil). Le build le valide et l'injecte dans `data.js` ;
l'accueil affiche ceux en `live` et `wip` (badge « en cours »), un clic ouvre un nouvel onglet.
Statuts : `live`, `wip`, `local` (pas encore en ligne, masqué), `idea` (masqué).

## Pages
Toutes reliées par la ligne de liens en haut à droite (Atlas · Review · Duels · Mix-ups · Compare · Quiz).
- `index.html` : carte, fiches, recherche ; boutons Weak spots (carte colorée par ta précision, tous trainers et duels), Compare, Quiz, Duels ; menu ☰ sur téléphone. Fiche pays : trainers en mode exploration, « Mixed up with », « Your results ».
- `daily.html` : révision du jour (2 × 30 min) ; la page Plonk It du jour vient d'abord de tes duels ; sauvegarde des progrès sur GitHub (repo privé).
- `games.html` : review de tes Duels et Team Duels (données de `geo-review`, liées une fois avec « Link review.json », restées dans le navigateur) : par pays, régions les plus dures, parties manche par manche, carte, coéquipiers.
- `confusions.html` : pays confondus, tous trainers et duels.
- `compare.html#pl/cz` : deux pays côte à côte.
- `quiz.html` : révision espacée des fiches.

## Données partagées (navigateur, même site que les trainers)
`tgm.stats.<app>` (résumé de chaque trainer), `tgm.confusions` (pays confondus), `tgm.duels.summary` (duels par pays, pour la révision) ; préférences `atlas.*`. La révision sauvegarde ces clés sur GitHub ; les parties (`duels.review`) n'en sortent pas.

## Outils
`build.cmd` (fiches, `data.js`, `tgm-core.js` recopié dans les trainers), `publish-all.cmd` (tests de fumée `tools\smoke.py` puis publication repo par repo), `check-links.cmd`, `tools\pwa.py` (hors ligne + installation).

## Recherche
Tape au clavier n'importe quand. Pays en anglais, en français ou code ISO ; types en anglais ou en français
(« car paraguay », « voiture paraguay », « phone br », « plaque pologne »). Entrée ouvre la fiche.

## Partage (GitHub Pages)
`images\` n'est pas publié : le build en garde une copie dans `thumbs\full\`.
Supprime la ligne `images/` de `.gitignore` si tu veux aussi sauvegarder les originaux sur GitHub.

## Relief
`relief.webp` : ombrage du relief (Natural Earth, domaine public) reprojeté dans la projection de `map.js`, affiché par-dessus les pays. Opacité réglable dans `index.html` (`#map .relief`).
