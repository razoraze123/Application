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


def _get_driver(headless: bool = False) -> webdriver.Chrome:
    options = webdriver.ChromeOptions()
    if headless:
        options.add_argument("--headless")
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    service = Service(ChromeDriverManager().install())
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
    return driver


def scrap_produits_par_ids(
    id_url_map: dict,
    ids_selectionnes: list,
    base_dir: str,
) -> None:
    fichier_excel = os.path.join(base_dir, "woocommerce_mix.xlsx")
    driver = _get_driver(headless=True)
    woocommerce_rows = []

    print(f"\n🚀 Début du scraping de {len(ids_selectionnes)} liens...\n")
    for idx, id_produit in enumerate(ids_selectionnes, start=1):
        url = id_url_map.get(id_produit)
        if not url:
            print(f"❌ ID introuvable dans le fichier : {id_produit}")
            continue

        print(f"🔎 [{idx}/{len(ids_selectionnes)}] {id_produit} → {url}")
        try:
            driver.get(url)
            time.sleep(random.uniform(2.5, 3.5))
            driver.execute_script(
                "window.scrollTo(0, document.body.scrollHeight * 0.3);"
            )
            time.sleep(2)

            product_name = driver.find_element(By.TAG_NAME, "h1").text.strip()
            base_sku = (
                re.sub(r'\W+', '-', product_name.lower())
                .strip("-")[:15]
                .upper()
            )
            product_price = ""

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
                            product_price = match.group(1).replace(",", ".")
                        break
                except Exception:
                    continue

            variant_labels = driver.find_elements(
                By.CSS_SELECTOR, "label.color-swatch"
            )
            visible_labels = [
                label for label in variant_labels if label.is_displayed()
            ]
            variant_names = []

            for label in visible_labels:
                try:
                    name = label.find_element(
                        By.CSS_SELECTOR, "span.sr-only"
                    ).text.strip()
                    variant_names.append(name)
                except Exception:
                    continue

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
            print(f"❌ Erreur sur {url} → {e}\n")
            continue

    driver.quit()
    df = pd.DataFrame(woocommerce_rows)
    df.to_excel(fichier_excel, index=False)
    print(f"\n📁 Données sauvegardées dans : {fichier_excel}")


def scrap_fiches_concurrents(
    id_url_map: dict,
    ids_selectionnes: list,
    base_dir: str,
) -> None:
    save_directory = os.path.join(base_dir, "fiches_concurrents")
    recap_excel_path = os.path.join(base_dir, "recap_concurrents.xlsx")
    driver = _get_driver(headless=False)

    os.makedirs(save_directory, exist_ok=True)
    recap_data = []
    total = len(ids_selectionnes)
    for idx, id_produit in enumerate(ids_selectionnes, start=1):
        url = id_url_map.get(id_produit)
        if not url:
            print(f"\n❌ ID introuvable dans le fichier : {id_produit}")
            recap_data.append(("?", "?", id_produit, "ID non trouvé"))
            continue

        print(f"\n📦 {idx} / {total}")
        print(f"🔗 {url} — ", end="")

        try:
            driver.get(url)
            time.sleep(random.uniform(2.5, 4.2))

            html = driver.page_source
            soup = BeautifulSoup(html, "html.parser")

            title_tag = (
                soup.find("h1", class_="product-single__title") or
                soup.find("h1", class_="product-info__title") or
                soup.find("h1")
            )
            if not title_tag:
                raise Exception("❌ Titre produit introuvable")
            title = title_tag.get_text(strip=True)
            filename = clean_filename(title) + ".txt"
            txt_path = os.path.join(save_directory, filename)

            description_div = None
            description_div = soup.find("div", {"id": "product_description"})
            if not description_div:
                container = soup.find("div", class_="accordion__content")
                if container:
                    description_div = container.find("div", class_="prose")
            if not description_div:
                description_div = soup.find("div", class_="prose")
            if not description_div:
                raise Exception("❌ Description introuvable")

            def convert_links(tag):
                for a in tag.find_all("a", href=True):
                    text = a.get_text(strip=True)
                    href = a['href']
                    markdown = f"[{text}]({href})"
                    a.replace_with(markdown)

            convert_links(description_div)
            raw_html = str(description_div)

            txt_content = f"<h1>{title}</h1>\n\n{raw_html}"
            with open(txt_path, "w", encoding="utf-8") as f2:
                f2.write(txt_content)

            print(f"✅ Extraction OK ({filename})")
            recap_data.append((filename, title, url, "Extraction OK"))
        except Exception as e:
            print(f"❌ Extraction Échec — {str(e)}")
            recap_data.append(("?", "?", url, "Extraction Échec"))

    df = pd.DataFrame(
        recap_data,
        columns=["Nom du fichier", "H1", "Lien", "Statut"],
    )
    df.to_excel(recap_excel_path, index=False)
    driver.quit()
    print("\n🎉 Extraction terminée. Résultats enregistrés dans :")
    print(f"- 📁 Fiches : {save_directory}")
    print(f"- 📊 Récapitulatif : {recap_excel_path}")


def export_fiches_concurrents_json(
    base_dir: str,
    taille_batch: int = 5,
) -> None:
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

    for i in range(0, len(fichiers_txt), taille_batch):
        batch = fichiers_txt[i:i + taille_batch]
        data_batch = []

        print(f"\n🔹 Batch {i // taille_batch + 1} : {len(batch)} fichiers")
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
                print(f"  ✅ {fichier} — h1: {h1[:50]}...")
            except Exception as e:
                print(f"  ⚠️ Erreur lecture {fichier}: {e}")
                continue
            id_global += 1

        nom_fichier_sortie = f"batch_{i // taille_batch + 1}.json"
        chemin_sortie = os.path.join(dossier_sortie, nom_fichier_sortie)
        with open(chemin_sortie, "w", encoding="utf-8") as f_json:
            json.dump(data_batch, f_json, ensure_ascii=False, indent=2)

        print(f"    ➡️ Batch sauvegardé : {nom_fichier_sortie}")

    print(
        f"\n✅ Export JSON terminé avec lots de {taille_batch} produits. "
        f"Fichiers créés dans : {dossier_sortie}"
    )
