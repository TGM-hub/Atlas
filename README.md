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

Types : landscape, language, architecture, plate, bollard, pole, sign, road-lines, phone, regions, cities, car, soil, flag, other.
`regions` : cartes de divisions administratives (provinces, kabupaten, régions) ; `cities` : villes (City Placer, fiches à venir) ; `other` : ce qui ne rentre nulle part.
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
Les six pages portent la même barre, au même endroit : « Atlas » (retour à la carte) et les onglets Explore · Review · Duels · Mix-ups · Quiz, la page courante soulignée. Compare n'est pas un onglet : on y arrive depuis une fiche pays ou la recherche. La barre et les styles communs (couleurs, police, formes) sont écrits par `tools\shell.py` entre des marqueurs `tgm-shell` : ne pas les modifier à la main.
- `index.html` (Explore) : carte, filtre par type d'indice, fiche pays, recherche ; voir « En-tête et filtre », « Fiche pays » et « Carte » plus bas. Sur téléphone, les pages et Dark cards sont dans le menu.
- `daily.html` : révision du jour (2 × 30 min) ; la page Plonk It du jour vient d'abord de tes duels ; sauvegarde des progrès sur GitHub (repo privé).
- `games.html` : review de tes Duels et Team Duels (données de `geo-review`, liées une fois avec « Link review.json », restées dans le navigateur) : par pays, régions les plus dures, parties manche par manche, carte, coéquipiers.
- `confusions.html` : pays confondus, tous trainers et duels.
- `compare.html#pl/cz` : deux pays côte à côte.
- `quiz.html` : révision espacée des fiches.

## Données partagées (navigateur, même site que les trainers)
`tgm.stats.<app>` (résumé de chaque trainer), `tgm.confusions` (pays confondus), `tgm.duels.summary` (duels par pays, pour la révision) ; préférences `atlas.*`. La révision sauvegarde ces clés sur GitHub ; les parties (`duels.review`) n'en sortent pas.

## Outils
`build.cmd` (fiches, `data.js`, `tgm-core.js` recopié dans les trainers), `publish-all.cmd` (tests de fumée `tools\smoke.py` puis publication repo par repo), `check-links.cmd`, `tools\pwa.py` (hors ligne + installation).
`tools\shell.py` : barre et styles communs des six pages (relancé par `build.cmd` ; `py tools\shell.py --check` dit si une page a divergé, et `smoke.py` le vérifie).

## En-tête et filtre
En haut : recherche, pages (Explore · Review · Duels · Mix-ups · Quiz, la page courante soulignée), réglages (roue : Dark cards). Compare s'ouvre depuis une fiche pays ou la recherche (« compare pl cz »).
Dessous, le filtre « Clue » : tous les types de `config.json`, toujours dans le même ordre et à la même place. Le nombre est celui des fiches du pays ouvert (sinon de tout l'Atlas) ; un carré sarcelle = pas de fiche mais un trainer ; grisé = rien. Un clic filtre, c'est tout.

## Fiche pays
Résumé (code, continent, tier, fiches, trainers, précision si tu as des stats), puis Compare, Quiz et les liens externes (Plonk It, Street View, Relief, LearnableMeta), puis les pays confondus sur une ligne.
Ensuite une rangée par type d'indice : les vignettes des fiches (clic = visionneuse) et les trainers qui couvrent ce pays pour ce type, avec ta précision dans ce trainer à partir de 3 réponses. « Nothing yet » liste les types sans rien.
Le bouton ↔ change la largeur du panneau : étroit, moitié, plein écran (la carte s'efface). Un type ou un cluster vu sur tous les pays s'affiche au moins à mi-largeur, en grille.

## Carte
Étiquettes : code ISO quand le pays est assez grand à l'écran, nom entier quand il y a la place ; les pays GeoGuessr passent d'abord et deux étiquettes ne se chevauchent jamais. Réglage « Map labels » (roue).
« Colour by » (en haut à gauche de la carte) : Coverage, My accuracy (ex-Weak spots : orange = faible, bleu = fort, hachures = moins de 3 réponses, contour pointillé = confondu récemment), Frequency (tier du pays dans GeoGuessr). La légende en bas à gauche suit.
Coverage : jaune = 2 fiches ou plus, jaune sourd = 1 fiche, bleu sarcelle = pas de fiche mais un trainer couvre le pays, terre = rien. Avec un type choisi, un trainer du type compte comme une fiche.
Boutons + / − / cadrer en bas à droite (touches `+` et `-`) ; zoom limité à ×12. Un pays ouvert par la recherche, un lien ou l'adresse est cadré avec ses voisins ; un pays cliqué sur la carte ne la déplace pas.
Le relief (`relief.webp`) se charge après la carte, et pas du tout sur un écran de téléphone.
Échap ferme une couche à la fois (pays ou cluster, puis filtre de type). Le bouton Retour du navigateur revient au pays précédent.

## Adresse
L'adresse suit ce qui est affiché et se partage telle quelle : `#pl` (pays), `#pl/plate` (pays + type), `#t/plate` (un type sur tous les pays), `#c/cyrillic` (cluster, `#c/cyrillic/language` avec un type) ; une fiche ouverte ajoute `@clé`. Un type inconnu est ignoré (`#pl/xyz` ouvre la Pologne). Retour revient au pays précédent avec son filtre.

## Auteur et lecteur
Réglage « Author tools » (roue) : allumé par défaut en local (`file://`, localhost), éteint sur le site publié. Éteint, il masque le tableau « To fill in », la ligne « Nothing yet » des fiches pays et les mentions « low res ».
« New since your last visit » (accueil) : fiches dont le fichier est plus récent que ta visite précédente ; à la première visite, celles des 14 derniers jours (« Added recently »). La date vient du fichier image (`added` dans `data.js`, écrit par le build) : une fiche régénérée redevient nouvelle.

## Recherche
Tape au clavier n'importe quand. Pays en anglais, en français ou code ISO ; types en anglais ou en français
(« car paraguay », « voiture paraguay », « phone br », « plaque pologne »). Entrée ouvre la fiche.
La recherche trouve aussi les trainers (« bollard france », « sign reader ») et les liens externes d'un pays (« plonk jp », « street view br », « relief no ») ; ils s'ouvrent dans un nouvel onglet (↗). Un nom de pays seul ouvre sa page. Champ vide : les 5 derniers pays ouverts.

## Tests
`py tools\test_atlas_ui.py` (Playwright, comme `smoke.py`) : en-tête du panneau, couverture et légende, zoom et cadrage, Retour et Échap, recherche, relief, type Regions. `py tools\test_atlas_ui.py t_search_robust` pour un seul test.

## Partage (GitHub Pages)
`images\` n'est pas publié : le build en garde une copie dans `thumbs\full\`.
Supprime la ligne `images/` de `.gitignore` si tu veux aussi sauvegarder les originaux sur GitHub.

## Relief
`relief.webp` : ombrage du relief (Natural Earth, domaine public) reprojeté dans la projection de `map.js`, affiché par-dessus les pays. Opacité réglable dans `index.html` (`#map .relief`).
