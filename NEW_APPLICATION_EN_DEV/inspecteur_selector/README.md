# Navigateur Inspecteur de Sélecteur

Ce sous-dossier contient un prototype de navigateur minimaliste permettant de récupérer rapidement le sélecteur CSS d'un élément sur une page web et de tester directement le module de scraping de liens.

## Fonctionnalités

- Navigateur intégré basé sur **QtWebEngine**
- Champ pour saisir une URL et charger la page
- Clic droit sur un élément pour copier son sélecteur CSS
- Lancement immédiat du scraping avec le sélecteur choisi
- Export possible des liens récupérés
- Thèmes clair/sombre et interface bilingue (FR/EN)

## Installation

```bash
pip install -r requirements.txt
```

## Utilisation

Exécutez `python inspecteur_selector.py` puis :

1. Entrez l'URL cible et cliquez sur *Charger*.
2. Naviguez librement dans la page affichée.
3. Faites un clic droit sur un élément et choisissez *Utiliser ce sélecteur* pour remplir automatiquement le champ de sélecteur.
4. Lancez le scraping pour tester la sélection et afficher les liens extraits.
5. Les liens peuvent être exportés au format TXT ou CSV.

## Dépendances

- PySide6 et QtWebEngine
- selenium
- webdriver-manager

## Limitations

Ce prototype sert uniquement de démonstrateur et n'inclut pas de gestion avancée des erreurs ni de support complet de l'XPath. Seul le sélecteur CSS est récupéré par défaut.
