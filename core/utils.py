import os
import re
import unicodedata


def clean_name(name: str) -> str:
    nfkd = unicodedata.normalize('NFKD', name)
    only_ascii = nfkd.encode('ASCII', 'ignore').decode('ASCII')
    return only_ascii.lower().replace('-', ' ').strip()


def clean_filename(name: str) -> str:
    nfkd = unicodedata.normalize('NFKD', name)
    only_ascii = nfkd.encode('ASCII', 'ignore').decode('ASCII')
    safe = re.sub(r"[^a-zA-Z0-9\- ]", "", only_ascii)
    safe = safe.replace(" ", "-").lower()
    return safe


def charger_liens_avec_id(base_dir: str) -> dict:
    """Charge le mapping ID -> URL depuis le fichier liens_avec_id.txt."""
    id_url_map = {}
    liens_id_txt = os.path.join(base_dir, "liens_avec_id.txt")
    if not os.path.exists(liens_id_txt):
        print(f"Fichier introuvable : {liens_id_txt}")
        return id_url_map
    with open(liens_id_txt, "r", encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split(" ", 1)
            if len(parts) == 2:
                identifiant, url = parts
                id_url_map[identifiant.upper()] = url
    return id_url_map


def charger_liens_avec_id_fichier(fichier: str) -> dict:
    """Charge le mapping ID -> URL depuis un fichier texte fourni."""
    id_url_map = {}
    if not os.path.exists(fichier):
        print(f"Fichier introuvable : {fichier}")
        return id_url_map
    with open(fichier, "r", encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split(" ", 1)
            if len(parts) == 2:
                identifiant, url = parts
                id_url_map[identifiant.upper()] = url
    return id_url_map


def extraire_ids_depuis_input(input_str: str) -> list:
    try:
        start_id, end_id = input_str.upper().split("-")
        start_num = int(start_id[1:])
        end_num = int(end_id[1:])
        return [f"A{i}" for i in range(start_num, end_num + 1)]
    except Exception:
        print("⚠️ Format invalide. Utilise le format A1-A5.")
        return []
