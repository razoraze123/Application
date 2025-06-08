"""Simple scraper for name/link pairs using requests."""

import csv
import logging

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


def scrape_collection(url: str, selector: str, output_csv: str) -> int:
    """Fetch elements matching ``selector`` on ``url`` and save name/link pairs."""
    exit_code = 0
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
    except Exception as err:
        logger.error("Failed to fetch %s: %s", url, err)
        return 1

    soup = BeautifulSoup(resp.text, "html.parser")
    seen = set()
    rows = []
    for elem in soup.select(selector):
        name = elem.get_text(strip=True)
        link = elem.get("href", "")
        if not name or name.isnumeric():
            continue
        key = (name, link)
        if key in seen:
            continue
        seen.add(key)
        rows.append({"name": name, "link": link})

    try:
        with open(output_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["name", "link"])
            writer.writeheader()
            writer.writerows(rows)
    except Exception as err:
        logger.error("Failed to write CSV %s: %s", output_csv, err)
        exit_code = 1
    return exit_code
