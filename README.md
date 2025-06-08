Scraper
Application de scraping modulaire avec interface graphique (PySide6)

Description
Scraper est une application Python dotée d’une interface graphique moderne (PySide6), conçue pour extraire facilement des données depuis des sites e-commerce concurrents (liens, images, fiches produits, variantes, etc.).
Le projet est évolutif : il est prévu d’intégrer plusieurs modules (scraping d’images, d’attributs, optimisation, etc.).
Usage strictement personnel.

Fonctionnalités prévues
Extraction automatique de fiches produits, images et variantes depuis des sites concurrents

Gestion multi-modules pour étendre les fonctionnalités (optimisation d’images, scraping avancé…)

Interface graphique épurée, facile à prendre en main

Dépendances principales
PySide6 – interface graphique

QtWebEngine – nécessaire pour le navigateur intégré (package PySide6-Qt6-WebEngine)

requests – requêtes HTTP simples

selenium – scraping dynamique

pandas – gestion et export de données

beautifulsoup4 – parsing HTML

lxml – parsing HTML/XML rapide

python-dotenv – gestion de la config et des clés privées (optionnel)

tqdm – barres de progression dans la console

Ajoutez les modules spécifiques au fur et à mesure de l’évolution du projet.

Installation
Clonez ce dépôt et installez les dépendances :

```bash
git clone <repo_url>
cd Application
pip install -r requirements.txt
```

Si vous utilisez des fichiers de configuration YAML, installez l'option
supplémentaire :

```bash
pip install .[yaml]
```

Ce fichier de dépendances est la référence unique pour l'ensemble du dépôt.

## Dépendances système
Avant d'utiliser l'application sous Linux, installez les bibliothèques système nécessaires pour PySide6 :

```bash
sudo apt update
sudo apt install -y libegl1 libgl1-mesa-glx libxkbcommon-x11-0
```

Utilisation
Lancez l’application :

```bash
python application_definitif.py
```
L’interface graphique s’ouvre : suivez les indications pour scraper les sites souhaités.
`application_definitif.py` est l’interface officielle maintenue dans ce dépôt.

## Application du thème Material Design avec qt-material
### Ce qui a été fait
Le projet utilise **qt-material** pour donner à l'interface un style Material Design.

### Code d'exemple
```python
from qt_material import apply_stylesheet
app = QApplication(sys.argv)
apply_stylesheet(app, theme='dark_purple.xml')
```

### Explication utilisateur
Pour changer de thème, remplacez `dark_purple.xml` par l’un des nombreux thèmes fournis dans qt-material (par exemple : `dark_amber.xml`, `dark_blue.xml`, `light_pink.xml`, etc.).

## Boutons et icônes

### Ce qui a été fait
Les boutons utilisent le style qt-material pour rester cohérents avec le thème. Une icône QtAwesome peut être ajoutée facilement.

### Code d'exemple
```python
import qtawesome as qta
from PySide6.QtWidgets import QPushButton

btn = QPushButton(qta.icon('fa5s.play'), "Lancer")
```

### Explication utilisateur
Changez le nom de l'icône (`fa5s.play`) ou le texte du bouton selon vos besoins.

## Interface et navigation

### Ce qui a été fait
Une barre latérale verticale regroupe maintenant les onglets *Scraping*, *Paramètres* et *Guide*.

### Code d'exemple
```
+-----------+-----------------------+
| Scraping  |                       |
| Paramètres|  Contenu affiché ici  |
| Guide     |                       |
+-----------+-----------------------+
```

### Explication utilisateur
Choisissez simplement un onglet dans la barre pour afficher son contenu et naviguer rapidement dans l'application.

Structure du projet (exemple)
css
Copier
Modifier
scraper/
│
├── application_definitif.py
├── requirements.txt
├── README.md
├── core/
│   └── [modules de scraping]
├── ui/
│   └── [modules d’interface]
└── utils/
    └── [fonctions utilitaires]
À venir
Ajout de modules spécialisés (scraping images, gestion des variantes, export CSV, etc.)

Optimisations d’images automatisées

Options avancées dans l’interface

## Paramètres avancés et customisation

### Ce qui a été fait
Un bouton permet déjà d'activer le mode sombre ou clair. D'autres réglages comme la police et la densité seront ajoutés.

### Code d'exemple
```python
apply_stylesheet(app, theme='dark_purple.xml', extra={'font_family': 'Roboto', 'density_scale': '0'})
```

### Explication utilisateur
Les paramètres seront stockés dans la configuration puis passés à `qt-material` via l'argument `extra` pour personnaliser le thème.

# Application

Note :
Ce projet est à usage strictement personnel et n’est pas destiné à une diffusion publique.
Des scripts prototypes sont disponibles dans `NEW_APPLICATION_EN_DEV/`, notamment `scraper_universel.py` qui propose une interface en ligne de commande.

📦 css-selector-generator
Ce dossier contient une librairie open source JavaScript embarquée pour générer automatiquement des sélecteurs CSS uniques à partir d’un élément du DOM.
Cette librairie est intégrée dans le projet pour permettre à l’application de :

Générer rapidement le sélecteur CSS optimal pour n’importe quel élément d’une page web.

Proposer une sélection semi-automatique ou automatique dans les modules de scraping (visual selector).

À propos
Source originale : fczbkk/css-selector-generator (GitHub)

Licence : MIT (usage libre, attribution recommandée)

Version embarquée : voir le fichier package.json dans le dossier

Utilisation dans ce projet
Le code est appelé par les modules d’inspection visuelle ou de scraping pour suggérer le meilleur sélecteur CSS à l’utilisateur.

Aucun serveur JS externe requis : le code fonctionne localement (embarqué via un mini-serveur Node.js, une Webview, ou appelé depuis Python grâce à des bindings si besoin).

Pour les développeurs
Modification : Toute adaptation locale doit respecter la licence MIT.

Mise à jour : Pour mettre à jour la librairie, remplacer le contenu du dossier avec la nouvelle version depuis le repo d’origine.

Remarque :
La librairie n’a pas d’impact sur le fonctionnement principal de l’application tant qu’elle n’est pas explicitement appelée par les modules de scraping ou l’inspecteur visuel.

## Exemple de rendu des résultats/logs

```
| Action    | Progression |
|-----------|-------------|
| Variantes | 2/10        |
| Fiches    | 5/10        |
| Export    | 1/3         |

Journal
-------
✅ Fiche 1 récupérée
...
```

## Conseils pour personnaliser l’UI responsive

### Ce qui a été fait
Des mises en page flexibles assurent que les widgets s'adaptent à la taille de la fenêtre.

### Code d'exemple
- Utilisez `QVBoxLayout` et `QHBoxLayout` pour empiler les éléments.
- `setSectionResizeMode(QHeaderView.Stretch)` évite une barre de défilement horizontale.

### Explication utilisateur
Modifiez les fichiers `style.qss` et `light.qss` pour ajuster la palette de couleurs ou la police tout en conservant la compatibilité avec **qt-material**.

## Récapitulatif des étapes et options de personnalisation

1. **Thème Material Design** : choisir un fichier de thème dans qt-material.
2. **Icônes QtAwesome** : changer le nom de l'icône et le texte du bouton.
3. **Navigation** : modifier la barre latérale pour ajouter ou réordonner les onglets.
4. **Paramètres avancés** : utiliser l'argument `extra` pour la police (`font_family`) ou la densité (`density_scale`).
5. **UI responsive** : ajuster les fichiers QSS pour la palette de couleurs et la police.

## Lancer `scraper_images.py` en ligne de commande

Le script `scraper_images.py` peut être exécuté directement sans l'interface graphique pour télécharger les images des produits.

### Configuration par défaut

Par défaut, le script utilise les clefs suivantes :

- `chrome_driver_path` : chemin du Chromedriver (``None`` pour utiliser `webdriver_manager`)
- `chrome_binary_path` : binaire de Chrome à utiliser
- `root_folder` : dossier où seront enregistrées les images (`"images"`)
- `links_file_path` : fichier texte contenant les URL des produits (`"links.txt"`)

### Exemple de fichier YAML

```yaml
chrome_driver_path: "/usr/local/bin/chromedriver"
chrome_binary_path: "/usr/bin/google-chrome"
root_folder: "images"
links_file_path: "links.txt"
```

Lancement avec un fichier de configuration :

```bash
python scraper_images.py --config config.yaml
```

### Options CLI principales

- `--links` : fichier contenant les URLs des produits
- `--selector` : sélecteur CSS des images (par défaut `.product-gallery__media img`)
- `--chrome-driver` et `--chrome-binary` : chemins personnalisés pour Chrome/Chromedriver
- `--root` : dossier de destination des images

Les arguments passés en ligne de commande écrasent les valeurs du fichier de configuration.

## Lancer `scraper_links.py` en ligne de commande

Le script `scraper_links.py` permet de récupérer les paires nom/lien d'une page en une commande.

```bash
python scraper_links.py --url https://exemple.com --selector "a.product" --output liens.csv
```

### Options CLI principales

- `--url` : page à analyser
- `--selector` : sélecteur CSS à appliquer
- `--output` : fichier CSV de destination (`links.csv` par défaut)

## Lancer `scraper_universel.py` en ligne de commande

Le script `scraper_universel.py` extrait des champs d'une page produit selon une correspondance JSON ou YAML. Un des arguments `--mapping-file` ou `--mapping` est obligatoire.

```bash
python -m NEW_APPLICATION_EN_DEV.scraper_universel --url https://exemple.com --mapping-file mapping.json
```

Exemple avec une correspondance inline :

```bash
python -m NEW_APPLICATION_EN_DEV.scraper_universel --url https://exemple.com --mapping '{"title": "h1", "price": ".price"}'
```

### Options CLI principales

- `--url` : page à analyser
- `--mapping-file` : fichier JSON ou YAML définissant les sélecteurs
- `--mapping` : chaîne JSON à utiliser directement

