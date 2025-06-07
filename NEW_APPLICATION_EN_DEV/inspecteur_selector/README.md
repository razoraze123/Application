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

Assurez‑vous de disposer de Python 3.8 ou plus récent, puis installez les
dépendances :

```bash
pip install -r requirements.txt
```

Cela installe notamment **PySide6**, **selenium**, **webdriver-manager**,
**websockets** et **QtWebEngine**. Veillez aussi à avoir Google Chrome ou
Chromium déjà installé ; `webdriver-manager` téléchargera automatiquement le
ChromeDriver adapté.

## Utilisation

Lancez le programme :

```bash
python inspecteur_selector.py
```

Au premier démarrage, l'application tente de localiser Chrome ou Chromium.
Si aucun navigateur n'est trouvé, une boîte de dialogue permet de sélectionner
manuellement l'exécutable (Chrome, Chromium ou éventuellement Edge). Une fois le
navigateur choisi, il démarre automatiquement avec le port de débogage `9222` et
un serveur WebSocket sur `localhost:8765`.

1. Entrez l'URL cible puis cliquez sur *Charger* : la page s'ouvre dans le
   navigateur contrôlé par Selenium.
2. Chargez l'extension décrite plus bas (uniquement la première fois).
3. Naviguez dans la page et faites un clic droit sur un élément pour envoyer son
   sélecteur CSS (ou XPath) à l'application.
4. Cliquez sur *Lancer le scraping* pour tester la sélection et afficher les
   liens extraits.
5. Les liens peuvent ensuite être exportés au format TXT ou CSV.

## Dépendances

- PySide6 et QtWebEngine
- selenium
- webdriver-manager
- websockets

## Limitations

Ce prototype sert uniquement de démonstrateur et n'inclut pas de gestion avancée des erreurs. L'XPath proposé est généré via un simple script JavaScript et peut ne pas couvrir tous les cas.

## Extension Chrome

Une extension minimaliste se trouve dans `chrome_extension/`. Pour la charger :

1. Ouvrez Chrome et accédez à `chrome://extensions/`.
2. Activez le mode développeur (coin supérieur droit).
3. Cliquez sur *Charger l'extension non empaquetée* et sélectionnez le dossier `chrome_extension`.
4. Lors d'un clic droit sur une page, l'extension enverra le sélecteur CSS et l'XPath de l'élément au serveur WebSocket (`ws://localhost:8765`).

## Compatibilité et réseau

Le prototype fonctionne sous Windows, macOS et Linux (tests réalisés
principalement sur Linux). Il nécessite que les ports locaux
`9222` (débogage Chrome) et `8765` (WebSocket) ne soient pas bloqués par un
pare‑feu. En environnement restreint, autorisez ces ports pour permettre la
communication entre le navigateur et l'application.

Lorsque plusieurs navigateurs Chromium sont installés, vous pouvez en choisir un
lors de la première exécution. **Chrome** et **Chromium** sont pris en charge ;
l'utilisation d'**Edge** peut fonctionner mais n'a pas été testée.

## Dépannage

Si aucun sélecteur n'est reçu :

* Vérifiez que l'extension est bien chargée dans le navigateur.
* Assurez‑vous que les ports `9222` et `8765` ne sont pas bloqués par un
  pare‑feu ou un logiciel de sécurité.
* Fermez toutes les fenêtres Chrome/Chromium avant de relancer le programme,
  afin que Selenium puisse ouvrir une nouvelle instance avec le bon port.
