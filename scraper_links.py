import argparse
from core.collection_scraper import scrape_collection


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scrape name/link pairs from a collection page"
    )
    parser.add_argument("--url", required=True, help="Page URL to scrape")
    parser.add_argument(
        "--selector",
        required=True,
        help="CSS selector for items containing links",
    )
    parser.add_argument(
        "--output",
        default="links.csv",
        help="Destination CSV file",
    )
    args = parser.parse_args()
    scrape_collection(args.url, args.selector, args.output)


if __name__ == "__main__":  # pragma: no cover - manual execution
    main()
