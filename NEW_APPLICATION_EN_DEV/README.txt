Scraper universel
=================

Ce dossier contient un prototype isolé permettant d'extraire des champs
arbitraires depuis n'importe quelle page web.

Utilisation rapide
------------------

Pour lancer un test automatique (page de démonstration) :

```
python -m NEW_APPLICATION_EN_DEV.scraper_universel
```

Pour extraire vos propres pages :

```
python -m NEW_APPLICATION_EN_DEV.scraper_universel --url "https://exemple.com" \
    --mapping '{"titre": "h1", "prix": ".price"}'
```

Ou bien :

```
python -m NEW_APPLICATION_EN_DEV.scraper_universel --url "https://exemple.com" \
    --mapping-file mapping.json
```

Le mapping est un fichier JSON ou YAML associant un nom de champ à un
sélecteur CSS ou XPath.
