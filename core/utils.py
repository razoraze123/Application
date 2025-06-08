"""Utility helpers for cleaning text and loading product mappings."""

import os
import re
import unicodedata
import logging

logger = logging.getLogger(__name__)


def clean_name(name: str) -> str:
    """Return a normalized string suitable for folder names."""
    nfkd = unicodedata.normalize("NFKD", name)
    only_ascii = nfkd.encode("ASCII", "ignore").decode("ASCII")
    return only_ascii.lower().replace("-", " ").strip()


def clean_filename(name: str) -> str:
    """Sanitize a product title for use as a file name."""
    nfkd = unicodedata.normalize("NFKD", name)
    only_ascii = nfkd.encode("ASCII", "ignore").decode("ASCII")
    safe = re.sub(r"[^a-zA-Z0-9\- ]", "", only_ascii)
    safe = safe.replace(" ", "-").lower()
    return safe


def charger_liens_avec_id(base_dir: str) -> dict:
    """Load ID→URL mapping from ``liens_avec_id.txt`` in *base_dir*."""
    id_url_map = {}
    liens_id_txt = os.path.join(base_dir, "liens_avec_id.txt")
    if not os.path.exists(liens_id_txt):
        logger.warning(f"Fichier introuvable : {liens_id_txt}")
        return id_url_map
    with open(liens_id_txt, "r", encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split(" ", 1)
            if len(parts) == 2:
                identifiant, url = parts
                id_url_map[identifiant.upper()] = url
    return id_url_map


def charger_liens_avec_id_fichier(fichier: str) -> dict:
    """Load ID→URL mapping from an explicit text file path."""
    id_url_map = {}
    if not os.path.exists(fichier):
        logger.warning(f"Fichier introuvable : {fichier}")
        return id_url_map
    with open(fichier, "r", encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split(" ", 1)
            if len(parts) == 2:
                identifiant, url = parts
                id_url_map[identifiant.upper()] = url
    return id_url_map


def extraire_ids_depuis_input(input_str: str) -> list:
    """Return a list of IDs from a range expression like ``A1-A3``."""
    try:
        start_id, end_id = input_str.upper().split("-")
        start_num = int(start_id[1:])
        end_num = int(end_id[1:])
        return [f"A{i}" for i in range(start_num, end_num + 1)]
    except Exception:
        logger.error("⚠️ Format invalide. Utilise le format A1-A5.")
        return []
