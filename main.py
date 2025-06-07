"""Command line interface to launch scraping routines."""

import os
import sys
import logging

from core.scraper import (
    scrap_produits_par_ids,
    scrap_fiches_concurrents,
    export_fiches_concurrents_json,
)
from core.utils import charger_liens_avec_id, extraire_ids_depuis_input


def demander_base_dir() -> str:
    default_dir = os.getcwd()
    prompt = (
        "\U0001f4c2 Dossier de travail (Entr\u00e9e pour "
        f"'{default_dir}'): "
    )
    rep = input(prompt).strip()
    return rep or default_dir


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("Bienvenue dans l'application de scraping!")
    base_dir = demander_base_dir()

    id_url_map = charger_liens_avec_id(base_dir)
    plage_input = input(
        "\U0001f7e2 Quels identifiants veux-tu scraper ? (ex: A1-A5): "
    ).strip()
    ids_selectionnes = extraire_ids_depuis_input(plage_input)

    if not ids_selectionnes:
        print("\u26d4 Aucun ID valide fourni. Arr\u00eat du script.")
        exit()

    if input(
        "\u25b6\ufe0f Lancer le scraping des variantes ? (oui/non): "
    ).strip().lower() == "oui":
        code = scrap_produits_par_ids(id_url_map, ids_selectionnes, base_dir)
        if code:
            sys.exit(code)

    message_fiche = (
        "\u25b6\ufe0f Lancer le scraping des fiches produits concurrents ?"
        " (oui/non): "
    )
    if input(message_fiche).strip().lower() == "oui":
        code = scrap_fiches_concurrents(id_url_map, ids_selectionnes, base_dir)
        if code:
            sys.exit(code)

    msg_export = (
        "\u25b6\ufe0f Voulez-vous exporter les fiches produits concurrents en"
        " lots JSON\u202f? (oui/non): "
    )
    if input(msg_export).strip().lower() == "oui":
        try:
            taille = input(
                "  \ud83d\udd39 Taille des lots (appuie Entr\u00e9e pour 5): "
            ).strip()
            taille_batch = int(taille) if taille else 5
        except Exception:
            print(
                "\u26a0\ufe0f Valeur invalide, on utilise la taille 5 par"
                " d\u00e9faut."
            )
            taille_batch = 5
        code = export_fiches_concurrents_json(base_dir, taille_batch)
        if code:
            sys.exit(code)
