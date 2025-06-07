import os
import time
import random
import urllib.request
import re
import unicodedata
from urllib.parse import urlparse
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import importlib.util
import argparse
from config_loader import load_config

# === CONFIGURATION ===
DEFAULT_CONFIG = {
    "chrome_driver_path": r"C:\\Users\\Lamine\\Desktop\\woocommerce\\code\\chromdrivers 137\\chromedriver-win64\\chromedriver.exe",
    "chrome_binary_path": r"C:\\Users\\Lamine\\Desktop\\woocommerce\\code\\chromdrivers 137\\chrome-win64\\chrome.exe",
    "root_folder": r"C:\\Users\\Lamine\\Desktop\\woocommerce\\code\\CODE POUR BOB\\images non optimiser",
    "links_file_path": r"C:\\Users\\Lamine\\Desktop\\woocommerce\\code\\CODE POUR BOB\\liens.txt",
}

parser = argparse.ArgumentParser(description="Scrape images from product pages")
parser.add_argument("--config", help="Path to YAML or JSON configuration file")
parser.add_argument(
    "--selector",
    default=".product-gallery__media img",
    help="CSS selector used to locate product images",
)
args = parser.parse_args()
selector = args.selector

config = DEFAULT_CONFIG.copy()
if args.config:
    try:
        config.update(load_config(args.config))
    except Exception as e:
        print(f"\u26a0\ufe0f Impossible de charger la configuration: {e}")

chrome_driver_path = config["chrome_driver_path"]
chrome_binary_path = config["chrome_binary_path"]
ROOT_FOLDER = config["root_folder"]

os.makedirs(ROOT_FOLDER, exist_ok=True)

# === IMPORT DES SUFFIXES PERSONNALISÉS ===
def import_custom_suffixes(path):
    spec = importlib.util.spec_from_file_location("custom_suffixes", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.custom_suffixes

suffix_file_path = r"C:\Users\Lamine\Desktop\woocommerce\code\custom_suffixes.py"
custom_suffixes = import_custom_suffixes(suffix_file_path)

# Slugifie toutes les clés du dictionnaire
def slugify(text):
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('utf-8')
    text = re.sub(r'[^\w\s-]', '', text.lower())
    return re.sub(r'[-\s]+', '-', text).strip('-')

custom_suffixes = {
    slugify(key): value for key, value in custom_suffixes.items()
}

# === LECTURE DES LIENS ===
def read_links_from_txt(path):
    with open(path, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]

links_file_path = config["links_file_path"]
product_urls = read_links_from_txt(links_file_path)

# === FONCTIONS UTILES ===
def clean_filename_slug(filename):
    filename = re.sub(r"-\d{3,4}", "", filename)
    filename = re.sub(r'[-]+', '-', filename)
    return filename.strip('-')

def get_image_title_from_url(url):
    path = urlparse(url).path
    filename = os.path.basename(path)
    name = filename.split(".")[0]
    name = clean_filename_slug(name)
    return name.replace("-", " ").strip()

def generate_filename_from_image_url(url, product_title):
    title = get_image_title_from_url(url)
    title_slug = slugify(product_title)
    suffix = random.choice(custom_suffixes.get(title_slug, ["accessoire tendance à découvrir"]))
    full_text = f"{title} – {suffix}"
    filename = slugify(full_text) + ".webp"
    return filename, full_text

def create_driver():
    options = Options()
    options.binary_location = chrome_binary_path  # <- ajout important
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    service = Service(chrome_driver_path)
    driver = webdriver.Chrome(service=service, options=options)
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    })
    return driver

# === LANCEMENT DU SCRAPING ===
driver = create_driver()
failed_images = []

for index, url in enumerate(product_urls):
    print(f"\n🔍 Produit {index + 1}/{len(product_urls)} : {url}")

    if index > 0 and index % 25 == 0:
        print("🔄 Redémarrage du navigateur pour libérer la mémoire...")
        driver.quit()
        time.sleep(3)
        driver = create_driver()

    try:
        driver.get(url)
        time.sleep(random.uniform(2.5, 4.5))

        raw_title = driver.title.strip().split("|")[0].strip()
        product_title = raw_title
        product_folder_name = slugify(raw_title)
        
        folder = os.path.join(ROOT_FOLDER, product_folder_name)
        os.makedirs(folder, exist_ok=True)

        images = driver.find_elements(By.CSS_SELECTOR, selector)
        print(f"🖼️ {len(images)} image(s) trouvée(s)")

        for i, img in enumerate(images):
            src = img.get_attribute("src")
            if not src:
                continue

            try:
                temp_path = os.path.join(folder, f"temp_{i}.webp")
                urllib.request.urlretrieve(src, temp_path)

                filename, alt_text = generate_filename_from_image_url(src, product_title)
                final_path = os.path.join(folder, filename)

                if os.path.exists(final_path):
                    os.remove(final_path)

                os.rename(temp_path, final_path)

                print(f"   ✅ Image {i+1} → {filename}")
                print(f"      ↪️ Texte ALT : {alt_text}")
                time.sleep(random.uniform(1, 2))

            except Exception as img_err:
                print(f"   ❌ Échec de téléchargement pour image {i+1} : {img_err}")
                failed_images.append((url, src))

        print(f"📁 Téléchargement terminé pour : {product_folder_name}")

    except Exception as e:
        print(f"❌ Erreur sur la page {url} : {e}")

    print("-" * 80)
    time.sleep(random.uniform(1.5, 3))

driver.quit()

# === RÉSUMÉ DES ERREURS ===
if failed_images:
    print("\n❗Images échouées :")
    for url, src in failed_images:
        print(f"Produit : {url} → Image : {src}")
    print(f"Total échouées : {len(failed_images)}")
else:
    print("\n✅ Toutes les images ont été téléchargées avec succès.")

print("\n🎯 SCRIPT TERMINÉ.")
