import time
from urllib.parse import urljoin

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager


def scrape_links(url: str, selector: str) -> list[str]:
    """Return list of product links found at *url* using *selector*.

    Relative links are converted to absolute URLs based on the page host.
    """
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options,
    )

    links: list[str] = []
    try:
        driver.get(url)
        time.sleep(2)  # simple wait, pagination/lazy loading handled later
        elements = driver.find_elements(By.CSS_SELECTOR, selector)
        for elem in elements:
            href = elem.get_attribute("href")
            if not href:
                continue
            full = urljoin(url, href)
            if "/products/" in full:
                links.append(full)
    finally:
        driver.quit()

    return links
