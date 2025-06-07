"""Utility helpers for scraping project."""

import logging

import os
import re
import unicodedata


def clean_name(name: str) -> str:
    """Return a simplified lowercase name without dashes."""
    nfkd = unicodedata.normalize("NFKD", name)
    only_ascii = nfkd.encode("ASCII", "ignore").decode("ASCII")
    return only_ascii.lower().replace("-", " ").strip()


def clean_filename(name: str) -> str:
    """Sanitize ``name`` for safe file creation."""
    nfkd = unicodedata.normalize("NFKD", name)
    only_ascii = nfkd.encode("ASCII", "ignore").decode("ASCII")
    safe = re.sub(r"[^a-zA-Z0-9\- ]", "", only_ascii)
    safe = safe.replace(" ", "-").lower()
    return safe


def charger_liens_avec_id(base_dir: str) -> dict:
    """Load ID to URL mapping from ``liens_avec_id.txt`` in ``base_dir``."""
    id_url_map = {}
    liens_id_txt = os.path.join(base_dir, "liens_avec_id.txt")
    if not os.path.exists(liens_id_txt):
        logging.warning("Fichier introuvable : %s", liens_id_txt)
        return id_url_map
    with open(liens_id_txt, "r", encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split(" ", 1)
            if len(parts) == 2:
                identifiant, url = parts
                id_url_map[identifiant.upper()] = url
    return id_url_map


def charger_liens_avec_id_fichier(fichier: str) -> dict:
    """Load ID to URL mapping from the given text ``fichier``."""
    id_url_map = {}
    if not os.path.exists(fichier):
        logging.warning("Fichier introuvable : %s", fichier)
        return id_url_map
    with open(fichier, "r", encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split(" ", 1)
            if len(parts) == 2:
                identifiant, url = parts
                id_url_map[identifiant.upper()] = url
    return id_url_map


def extraire_ids_depuis_input(input_str: str) -> list:
    """Return a list of IDs given a range like ``A1-A5``."""
    try:
        start_id, end_id = input_str.upper().split("-")
        start_num = int(start_id[1:])
        end_num = int(end_id[1:])
        return [f"A{i}" for i in range(start_num, end_num + 1)]
    except ValueError:
        logging.warning("Format invalide. Utilise le format A1-A5.")
        return []
