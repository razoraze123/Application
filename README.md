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

Note :
Ce projet est à usage strictement personnel et n’est pas destiné à une diffusion publique.

Le dossier `NEW_APPLICATION_EN_DEV/` contient des scripts prototypes (tel que
`interface_dev.py`) et ne constitue pas l’application officielle.

# Application

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


