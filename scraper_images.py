"""Command line interface for :class:`core.image_scraper.ImageScraper`."""

import argparse
from config_loader import load_config
from core.image_scraper import ImageScraper

DEFAULT_CONFIG = {
    "chrome_driver_path": None,
    "chrome_binary_path": None,
    "root_folder": "images",
    "links_file_path": "links.txt",
}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scrape images from product pages",
    )
    parser.add_argument(
        "--config",
        help="Path to YAML or JSON configuration file",
    )
    parser.add_argument(
        "--links",
        help="Text file containing product URLs",
    )
    parser.add_argument(
        "--selector",
        default=".product-gallery__media img",
        help="CSS selector used to locate product images",
    )
    parser.add_argument("--chrome-driver", dest="chrome_driver")
    parser.add_argument("--chrome-binary", dest="chrome_binary")
    parser.add_argument("--root", dest="root_folder")
    args = parser.parse_args()

    config = DEFAULT_CONFIG.copy()
    if args.config:
        config.update(load_config(args.config))

    chrome_driver = args.chrome_driver or config.get("chrome_driver_path")
    chrome_binary = args.chrome_binary or config.get("chrome_binary_path")
    root_folder = args.root_folder or config.get("root_folder")
    links_file = args.links or config.get("links_file_path")

    scraper = ImageScraper(
        chrome_driver_path=chrome_driver,
        chrome_binary_path=chrome_binary,
        root_folder=root_folder,
        selector=args.selector,
    )

    urls = scraper.load_urls(links_file)
    scraper.scrape_images(urls)


if __name__ == "__main__":  # pragma: no cover - manual execution only
    main()
