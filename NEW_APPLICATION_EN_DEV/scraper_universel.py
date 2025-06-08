"""Simple configurable scraper for e-commerce product pages."""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

import requests
from bs4 import BeautifulSoup

try:
    from lxml import html  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    html = None

logger = logging.getLogger(__name__)


def _load_mapping(mapping: Optional[Dict[str, str]] = None,
                  mapping_file: Optional[str] = None) -> Dict[str, str]:
    """Return a mapping dict loaded from *mapping_file* or *mapping*."""
    if mapping:
        return mapping
    if not mapping_file:
        raise ValueError("No mapping provided")

    path = Path(mapping_file)
    if not path.exists():
        raise FileNotFoundError(mapping_file)
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in {".yaml", ".yml"}:
        try:
            import yaml  # type: ignore
        except Exception as exc:  # pragma: no cover - optional dependency
            raise ImportError("pyyaml required for YAML mapping") from exc
        return yaml.safe_load(text)
    return json.loads(text)


def _extract_with_css(soup: BeautifulSoup, selector: str) -> Optional[str]:
    elems = soup.select(selector)
    if not elems:
        return None
    elem = elems[0]
    if elem.name == "img" and elem.has_attr("src"):
        return elem["src"].strip()
    text = elem.get_text(strip=True)
    return text or None


def _extract_with_xpath(tree: "html.HtmlElement", selector: str) -> Optional[str]:
    if tree is None:
        return None
    results = tree.xpath(selector)
    if not results:
        return None
    result = results[0]
    if hasattr(result, "text_content"):
        return result.text_content().strip()
    if isinstance(result, str):
        return result.strip()
    return str(result).strip()


def scrap_fiche_generique(url: str,
                          mapping: Optional[Dict[str, str]] = None,
                          *,
                          mapping_file: Optional[str] = None,
                          timeout: int = 10) -> Dict[str, Any]:
    """Return the scraped fields defined in *mapping* from *url*."""
    mapping = _load_mapping(mapping, mapping_file)

    try:
        resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()
    except requests.exceptions.RequestException as err:
        logger.error("Failed to fetch %s: %s", url, err)
        return {}

    page = resp.text
    soup = BeautifulSoup(page, "html.parser")
    tree = html.fromstring(page) if html else None

    data: Dict[str, Any] = {}
    for field, selector in mapping.items():
        value: Optional[str] = None
        if selector.lstrip().startswith("/"):
            value = _extract_with_xpath(tree, selector)
        else:
            value = _extract_with_css(soup, selector)

        if not value:
            logger.warning("Champ manquant: %s via %s", field, selector)
        data[field] = value
    return data


def main() -> None:
    """Simple command line interface for :func:`scrap_fiche_generique`."""
    parser = argparse.ArgumentParser(description="Universal scraper")
    parser.add_argument("--url", required=True, help="URL of the page")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--mapping-file",
        help="JSON or YAML mapping file",
    )
    group.add_argument(
        "--mapping",
        help="Mapping JSON string",
    )

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    mapping = json.loads(args.mapping) if args.mapping else None
    data = scrap_fiche_generique(
        args.url, mapping, mapping_file=args.mapping_file
    )
    print(json.dumps(data, ensure_ascii=False))


if __name__ == "__main__":  # pragma: no cover - CLI
    main()

