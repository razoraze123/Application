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
