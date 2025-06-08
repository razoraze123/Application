"""Selenium based scraping helpers."""

import os
import re
import json
import time
import random
import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

from .utils import clean_name, clean_filename
import logging

logger = logging.getLogger(__name__)


def _get_driver(headless: bool = False) -> webdriver.Chrome:
    options = webdriver.ChromeOptions()
    if headless:
        options.add_argument("--headless")
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    service = Service(ChromeDriverManager().install())
    try:
        driver = webdriver.Chrome(service=service, options=options)
        driver.execute_cdp_cmd(
            "Page.addScriptToEvaluateOnNewDocument",
            {
                "source": (
                    "Object.defineProperty("
                    "navigator, 'webdriver', {get: () => undefined})"
                )
            },
        )
    except Exception as err:
        logger.error("Unable to start Chrome driver: %s", err)
        raise
    return driver


def _parse_price(driver: webdriver.Chrome) -> str:
    """Return the product price displayed on the current page."""
    for selector in [
        "sale-price.text-lg",
        ".price",
        ".product-price",
        ".woocommerce-Price-amount",
    ]:
        try:
            elem = driver.find_element(By.CSS_SELECTOR, selector)
            if elem and elem.text.strip():
                match = re.search(
                    r"([0-9]+(?:[\\.,][0-9]{2})?)",
                    elem.text.strip(),
                )
                if match:
                    return match.group(1).replace(",", ".")
        except Exception:
            continue
    return ""


def _get_variant_names(driver: webdriver.Chrome) -> list:
    """Return the visible variant names on the current page."""
    labels = driver.find_elements(By.CSS_SELECTOR, "label.color-swatch")
    names = []
    for label in labels:
        if not label.is_displayed():
            continue
        try:
            elem = label.find_element(By.CSS_SELECTOR, "span.sr-only")
            names.append(elem.text.strip())
        except Exception:
            continue
    return names


def _extract_title(soup: BeautifulSoup) -> str:
    """Return the product title from *soup* or raise."""
    title_tag = (
        soup.find("h1", class_="product-single__title")
        or soup.find("h1", class_="product-info__title")
        or soup.find("h1")
    )
    if not title_tag:
        raise Exception("❌ Titre produit introuvable")
    return title_tag.get_text(strip=True)


def _find_description_div(soup: BeautifulSoup) -> BeautifulSoup:
    """Return the description div from *soup* or raise."""
    description_div = soup.find("div", {"id": "product_description"})
    if not description_div:
        container = soup.find("div", class_="accordion__content")
        if container:
            description_div = container.find("div", class_="prose")
    if not description_div:
        description_div = soup.find("div", class_="prose")
    if not description_div:
        raise Exception("❌ Description introuvable")
    return description_div


def _convert_links(tag):
    """Replace HTML links within *tag* by Markdown text."""
    for a in tag.find_all("a", href=True):
        text = a.get_text(strip=True)
        href = a["href"]
        markdown = f"[{text}]({href})"
        a.replace_with(markdown)


def scrap_produits_par_ids(
    id_url_map: dict,
    ids_selectionnes: list,
    base_dir: str,
    headless: bool = False,
) -> int:
    """Scrape product variants and generate a WooCommerce spreadsheet.

    Parameters
    ----------
    headless : bool, optional
        If ``True`` Selenium runs without opening a browser window.
    """
    fichier_excel = os.path.join(base_dir, "woocommerce_mix.xlsx")
    driver = None
    woocommerce_rows = []
    exit_code = 0
    try:
        driver = _get_driver(headless=headless)

        logger.info(
            "🚀 Début du scraping de %d liens...",
            len(ids_selectionnes),
        )
        for idx, id_produit in enumerate(ids_selectionnes, start=1):
            url = id_url_map.get(id_produit)
            if not url:
                logger.warning(
                    "ID introuvable dans le fichier : %s",
                    id_produit,
                )
                continue

            logger.info(
                "🔎 [%d/%d] %s → %s",
                idx,
                len(ids_selectionnes),
                id_produit,
                url,
            )
            try:
                driver.get(url)
                time.sleep(random.uniform(2.5, 3.5))
                driver.execute_script(
                    "window.scrollTo(0, document.body.scrollHeight * 0.3);"
                )
                time.sleep(2)

                name_el = driver.find_element(By.TAG_NAME, "h1")
                product_name = name_el.text.strip()
                base_sku = (
                    re.sub(r'\W+', '-', product_name.lower())
                    .strip("-")[:15]
                    .upper()
                )
                product_price = _parse_price(driver)

                variant_names = _get_variant_names(driver)

                nom_dossier = clean_name(product_name).replace(" ", "-")

                if len(variant_names) <= 1:
                    woocommerce_rows.append({
                        "ID Produit": id_produit,
                        "Type": "simple",
                        "SKU": base_sku,
                        "Name": product_name,
                        "Regular price": product_price,
                        "Nom du dossier": nom_dossier
                    })
                    continue

                woocommerce_rows.append({
                    "ID Produit": id_produit,
                    "Type": "variable",
                    "SKU": base_sku,
                    "Name": product_name,
                    "Parent": "",
                    "Attribute 1 name": "Couleur",
                    "Attribute 1 value(s)": " | ".join(variant_names),
                    "Attribute 1 default": variant_names[0],
                    "Regular price": "",
                    "Nom du dossier": nom_dossier
                })

                for v in variant_names:
                    clean_v = re.sub(r'\W+', '', v).upper()
                    child_sku = f"{base_sku}-{clean_v}"
                    woocommerce_rows.append({
                        "ID Produit": id_produit,
                        "Type": "variation",
                        "SKU": child_sku,
                        "Name": "",
                        "Parent": base_sku,
                        "Attribute 1 name": "Couleur",
                        "Attribute 1 value(s)": v,
                        "Regular price": product_price,
                        "Nom du dossier": nom_dossier
                    })

            except Exception as e:
                exit_code = 1
                logger.error("Erreur sur %s → %s", url, e)
                continue

    finally:
        if driver:
            driver.quit()
        df = pd.DataFrame(woocommerce_rows)
        df.to_excel(fichier_excel, index=False)
        logger.info("📁 Données sauvegardées dans : %s", fichier_excel)
    return exit_code


def scrap_fiches_concurrents(
    id_url_map: dict,
    ids_selectionnes: list,
    base_dir: str,
    headless: bool = False,
) -> int:
    """Extract competitor pages as HTML snippets.

    Parameters
    ----------
    headless : bool, optional
        Run Selenium without GUI when ``True``.
    """
    save_directory = os.path.join(base_dir, "fiches_concurrents")
    recap_excel_path = os.path.join(base_dir, "recap_concurrents.xlsx")
    driver = None
    exit_code = 0
    recap_data = []
    try:
        driver = _get_driver(headless=headless)

        os.makedirs(save_directory, exist_ok=True)
        total = len(ids_selectionnes)
        for idx, id_produit in enumerate(ids_selectionnes, start=1):
            url = id_url_map.get(id_produit)
            if not url:
                logger.warning(
                    "ID introuvable dans le fichier : %s",
                    id_produit,
                )
                recap_data.append(("?", "?", id_produit, "ID non trouvé"))
                continue

            logger.info("📦 %d / %d", idx, total)
            logger.info("🔗 %s —", url)

            try:
                driver.get(url)
                time.sleep(random.uniform(2.5, 4.2))

                html = driver.page_source
                soup = BeautifulSoup(html, "html.parser")

                title = _extract_title(soup)
                filename = clean_filename(title) + ".txt"
                txt_path = os.path.join(save_directory, filename)

                description_div = _find_description_div(soup)
                _convert_links(description_div)
                raw_html = str(description_div)

                txt_content = f"<h1>{title}</h1>\n\n{raw_html}"
                with open(txt_path, "w", encoding="utf-8") as f2:
                    f2.write(txt_content)

                logger.info("✅ Extraction OK (%s)", filename)
                recap_data.append((filename, title, url, "Extraction OK"))
            except Exception as e:
                exit_code = 1
                logger.error("❌ Extraction Échec — %s", str(e))
                recap_data.append(("?", "?", url, "Extraction Échec"))

    finally:
        if driver:
            driver.quit()
        df = pd.DataFrame(
            recap_data,
            columns=["Nom du fichier", "H1", "Lien", "Statut"],
        )
        df.to_excel(recap_excel_path, index=False)
        logger.info("🎉 Extraction terminée. Résultats enregistrés dans :")
        logger.info("- 📁 Fiches : %s", save_directory)
        logger.info("- 📊 Récapitulatif : %s", recap_excel_path)
    return exit_code


def export_fiches_concurrents_json(
    base_dir: str,
    taille_batch: int = 5,
) -> int:
    """Export scraped pages to JSON batches of ``taille_batch`` files."""
    dossier_source = os.path.join(base_dir, "fiches_concurrents")
    dossier_sortie = os.path.join(dossier_source, "batches_json")
    os.makedirs(dossier_sortie, exist_ok=True)
    fichiers_txt = [
        f for f in os.listdir(dossier_source) if f.endswith(".txt")
    ]
    fichiers_txt.sort()
    id_global = 1

    def extraire_h1(html: str) -> str:
        match = re.search(
            r"<h1[^>]*>(.*?)</h1>",
            html,
            re.IGNORECASE | re.DOTALL,
        )
        return match.group(1).strip() if match else ""

    exit_code = 0
    try:
        for i in range(0, len(fichiers_txt), taille_batch):
            batch = fichiers_txt[i:i + taille_batch]
            data_batch = []

            logger.info(
                "🔹 Batch %d : %d fichiers",
                i // taille_batch + 1,
                len(batch),
            )
            for fichier in batch:
                chemin = os.path.join(dossier_source, fichier)
                try:
                    with open(chemin, "r", encoding="utf-8") as f:
                        contenu = f.read()
                    h1 = extraire_h1(contenu)
                    id_source = os.path.splitext(fichier)[0]
                    data_batch.append({
                        "id": id_global,
                        "id_source": id_source,
                        "nom": fichier,
                        "h1": h1,
                        "html": contenu.strip()
                    })
                    logger.info("  ✅ %s — h1: %s...", fichier, h1[:50])
                except Exception as e:
                    exit_code = 1
                    logger.warning("  ⚠️ Erreur lecture %s: %s", fichier, e)
                    continue
                id_global += 1

            nom_fichier_sortie = f"batch_{i // taille_batch + 1}.json"
            chemin_sortie = os.path.join(dossier_sortie, nom_fichier_sortie)
            with open(chemin_sortie, "w", encoding="utf-8") as f_json:
                json.dump(data_batch, f_json, ensure_ascii=False, indent=2)

            logger.info("    ➡️ Batch sauvegardé : %s", nom_fichier_sortie)
    finally:
        logger.info(
            "✅ Export JSON terminé avec lots de %d produits. "
            "Fichiers créés dans : %s",
            taille_batch,
            dossier_sortie,
        )
    return exit_code
