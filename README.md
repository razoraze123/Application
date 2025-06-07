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

Des scripts prototypes étaient présents dans `NEW_APPLICATION_EN_DEV/`. Ce dossier a été supprimé pour clarifier la version officielle.

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
