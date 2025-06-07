# Navigateur Inspecteur de Sélecteur

Ce sous-dossier contient un prototype de navigateur minimaliste permettant de récupérer rapidement le sélecteur CSS d'un élément sur une page web et de tester directement le module de scraping de liens.

## Fonctionnalités

- Navigateur intégré basé sur **QtWebEngine**
- Champ pour saisir une URL et charger la page
- Clic droit sur un élément pour copier son sélecteur CSS ou son XPath
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
3. Faites un clic droit sur un élément et choisissez *Utiliser ce sélecteur* ou *Utiliser l'XPath* pour remplir automatiquement le champ.
4. Lancez le scraping pour tester la sélection et afficher les liens extraits.
5. Les liens peuvent être exportés au format TXT ou CSV.

## Dépendances

- PySide6 et QtWebEngine
- selenium
- webdriver-manager

## Limitations

Ce prototype sert uniquement de démonstrateur et n'inclut pas de gestion avancée des erreurs. L'XPath proposé est généré via un simple script JavaScript et peut ne pas couvrir tous les cas.

## Extension Chrome

Une extension minimaliste se trouve dans `chrome_extension/`. Pour la charger :

1. Ouvrez Chrome et accédez à `chrome://extensions/`.
2. Activez le mode développeur (coin supérieur droit).
3. Cliquez sur *Charger l'extension non empaquetée* et sélectionnez le dossier `chrome_extension`.
4. Lors d'un clic droit sur une page, l'extension enverra le sélecteur CSS et l'XPath de l'élément au serveur WebSocket (`ws://localhost:8765`).
