"""Universal product page scraper.

This module exposes :func:`extract_fields` which downloads a page and
extracts fields based on a mapping of names to CSS selectors or XPath
expressions. When executed as a script without arguments, a demo scrape
is performed on a page from https://books.toscrape.com/.

Architecture
------------
- ``extract_fields`` : pure function containing the scraping logic.
- ``scrap_fiche_generique`` : wrapper allowing a mapping dict or mapping
  file.
- ``main`` : command line interface. If called without parameters, the
  demo run is triggered. Otherwise ``--url`` and a mapping definition
  are expected.

CLI usage
---------

``python -m NEW_APPLICATION_EN_DEV.scraper_universel --url URL --mapping-file map.json``

Known limitations
-----------------
- Optional dependency ``lxml`` is required for XPath extraction.
- Only the first matching element was previously returned (now lists are
  supported).
"""

# ---------------------------------------------------------------------------
# TODO/ACTION comments
# ---------------------------------------------------------------------------
# TODO: validate mapping types and raise a clear error for malformed
#       definitions. ACTION: add checks in ``_load_mapping`` and
#       ``extract_fields``.
# TODO: handle invalid CSS/XPath selectors gracefully. ACTION: wrap
#       extraction helpers in try/except blocks with explicit logs.
# TODO: support extraction of multiple values. ACTION: return a list when
#       several nodes match the selector.
# TODO: provide verbose logging option and allow a custom User-Agent.
#       ACTION: expose ``verbose`` and ``user_agent`` parameters.
# TODO: integrate simple self tests. ACTION: ``_selftest`` runnable via
#       ``--self-test`` CLI argument.

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, Union

import requests
from bs4 import BeautifulSoup

try:
    from lxml import html  # type: ignore
    from lxml.html import HtmlElement  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    html = None
    HtmlElement = Any  # type: ignore

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# utility helpers
# ---------------------------------------------------------------------------


def _load_mapping(
    mapping: Optional[Dict[str, Any]] = None, mapping_file: Optional[str] = None
) -> Dict[str, Any]:
    """Return a mapping dict loaded from *mapping_file* or *mapping*."""

    if mapping is not None:
        if not isinstance(mapping, dict) or not all(
            isinstance(k, str) and isinstance(v, (str, dict)) for k, v in mapping.items()
        ):
            raise ValueError(
                "mapping must be a dict with str keys and str or dict values"
            )
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
        try:
            return yaml.safe_load(text)
        except Exception as exc:
            raise ValueError(f"Invalid YAML mapping: {exc}") from exc
    try:
        return json.loads(text)
    except Exception as exc:
        raise ValueError(f"Invalid JSON mapping: {exc}") from exc


def clean_description(text: str) -> str:
    lines = text.splitlines()
    ignored_keywords = [
        "livraison",
        "retour",
        "contact",
        "paiement",
        "bob crew",
        "service client",
    ]
    return "\n".join(
        line
        for line in lines
        if len(line.strip()) > 30
        and not any(kw in line.lower() for kw in ignored_keywords)
    )


def _extract_with_css(
    soup: BeautifulSoup, selector: Union[str, Dict[str, Any]]
) -> Optional[Union[str, list[str]]]:
    """Return the text of the first match or a list for multiple matches."""

    options: Dict[str, Any] = {}
    css = selector
    if isinstance(selector, dict):
        css = selector.get("selector")
        if not isinstance(css, str):
            logger.error("Invalid mapping: missing selector in %s", selector)
            return None
        options = selector

    try:
        elems = soup.select(css) if isinstance(css, str) else []
    except Exception as exc:  # malformed selector
        logger.error("Invalid CSS selector %s: %s", css, exc)
        return None
    if not elems:
        return None

    values: list[str] = []
    for elem in elems:
        target = elem
        if options.get("first_paragraph"):
            first = elem.select_one("p")
            if first is not None:
                target = first
        if target.name == "img" and target.has_attr("src"):
            values.append(target["src"].strip())
            continue

        if options.get("raw_html"):
            text = target.decode_contents()
        else:
            text = target.get_text(separator="\n", strip=True)
        if options.get("clean"):
            text = clean_description(text)
        if text:
            values.append(text)

    if not values:
        return None
    return values[0] if len(values) == 1 else values


def _extract_with_xpath(
    tree: Optional[HtmlElement], selector: str
) -> Optional[Union[str, list[str]]]:
    """Return the text of the first match or a list for multiple matches."""

    if tree is None:
        return None
    try:
        results = tree.xpath(selector)
    except Exception as exc:  # malformed selector
        logger.error("Invalid XPath %s: %s", selector, exc)
        return None
    if not results:
        return None

    values: list[str] = []
    for result in results:
        if hasattr(result, "text_content"):
            values.append(result.text_content().strip())
        elif isinstance(result, str):
            values.append(result.strip())
        else:
            values.append(str(result).strip())

    return values[0] if len(values) == 1 else values


# ---------------------------------------------------------------------------
# public API
# ---------------------------------------------------------------------------


def extract_fields(
    url: str,
    mapping: Dict[str, Any],
    *,
    timeout: int = 10,
    user_agent: Optional[str] = None,
    verbose: bool = False,
) -> Dict[str, Any]:
    """Download *url* and return the fields defined in *mapping*.

    Parameters
    ----------
    url:
        Page to scrape.
    mapping:
        Dictionary where keys are field names and values are CSS selectors,
        XPath expressions or a dictionary with advanced options.
    timeout:
        Request timeout in seconds.
    user_agent:
        Optional user agent header used for the request.
    verbose:
        When ``True`` debug information is logged.
    """
    if not isinstance(mapping, dict) or not all(
        isinstance(k, str) and isinstance(v, (str, dict)) for k, v in mapping.items()
    ):
        raise ValueError(
            "mapping must be a dict with str keys and str or dict values"
        )

    headers = {"User-Agent": user_agent} if user_agent else None
    if verbose:
        logger.setLevel(logging.DEBUG)

    req_kwargs = {"timeout": timeout}
    if headers:
        req_kwargs["headers"] = headers

    try:
        resp = requests.get(url, **req_kwargs)
        resp.raise_for_status()
    except requests.exceptions.RequestException as err:
        logger.error("Failed to fetch %s: %s", url, err)
        return {}

    page = resp.text
    bs_parser = "lxml" if html else "html.parser"
    soup = BeautifulSoup(page, bs_parser)
    tree = html.fromstring(page) if html else None

    data: Dict[str, Any] = {}
    for field, selector in mapping.items():
        value: Optional[Union[str, list[str]]] = None
        if isinstance(selector, dict):
            value = _extract_with_css(soup, selector)
        elif isinstance(selector, str) and selector.lstrip().startswith("/"):
            value = _extract_with_xpath(tree, selector)
        else:
            value = _extract_with_css(soup, selector)

        if not value:
            logger.warning("Champ manquant: %s via %s", field, selector)
        data[field] = value
    return data


def scrap_fiche_generique(
    url: str,
    mapping: Optional[Dict[str, Any]] = None,
    *,
    mapping_file: Optional[str] = None,
    timeout: int = 10,
    user_agent: Optional[str] = None,
    verbose: bool = False,
) -> Dict[str, Any]:
    """Backward compatible wrapper around :func:`extract_fields`."""

    resolved = _load_mapping(mapping, mapping_file)
    return extract_fields(
        url, resolved, timeout=timeout, user_agent=user_agent, verbose=verbose
    )


def _selftest() -> None:
    """Run a minimal test suite on the module."""
    import unittest
    from unittest.mock import patch

    class DummyResponse:
        def __init__(self, text: str):
            self.text = text

        def raise_for_status(self) -> None:  # pragma: no cover - dummy
            pass

    class Tests(unittest.TestCase):
        def test_success(self) -> None:
            html_page = "<html><h1>Hello</h1></html>"
            with patch("requests.get", return_value=DummyResponse(html_page)):
                res = extract_fields("http://x", {"title": "h1"})
                self.assertEqual(res["title"], "Hello")

        def test_missing(self) -> None:
            html_page = "<html><h1>Hello</h1></html>"
            with patch("requests.get", return_value=DummyResponse(html_page)):
                res = extract_fields("http://x", {"desc": ".desc"})
                self.assertIsNone(res["desc"])

        def test_bad_mapping(self) -> None:
            with self.assertRaises(ValueError):
                scrap_fiche_generique("http://x", {"title": 123})

    unittest.main(argv=["_selftest"], exit=False)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: Optional[list[str]] = None) -> None:
    """Entry point for the command line interface."""
    if argv is None:
        argv = sys.argv[1:]

    if not argv:
        demo_url = (
            "https://books.toscrape.com/catalogue/"
            "a-light-in-the-attic_1000/index.html"
        )
        demo_mapping = {
            "titre": "h1",
            "prix": ".price_color",
            "disponibilite": "//p[contains(@class,'instock')]",
        }
        data = extract_fields(demo_url, demo_mapping)
        print(json.dumps(data, ensure_ascii=False))
        return

    parser = argparse.ArgumentParser(description="Universal scraper")
    parser.add_argument("--url", required=False, help="URL of the page")
    parser.add_argument("--self-test", action="store_true", help="run self tests")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--mapping-file",
        help="JSON or YAML mapping file",
    )
    group.add_argument(
        "--mapping",
        help="Mapping JSON string",
    )
    parser.add_argument(
        "--user-agent",
        help="custom user agent",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="enable debug logs",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO)

    if args.self_test:
        _selftest()
        return

    if not args.url:
        parser.error("--url is required unless --self-test is used")

    mapping = json.loads(args.mapping) if args.mapping else None
    data = scrap_fiche_generique(
        args.url,
        mapping,
        mapping_file=args.mapping_file,
        user_agent=args.user_agent,
        verbose=args.verbose,
    )
    print(json.dumps(data, ensure_ascii=False))


if __name__ == "__main__":  # pragma: no cover - CLI
    main()
