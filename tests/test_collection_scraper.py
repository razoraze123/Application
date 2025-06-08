import csv
import requests
from core.collection_scraper import scrape_collection


class FakeResponse:
    def __init__(self, text):
        self.text = text

    def raise_for_status(self):
        pass


def test_scrape_collection_basic(monkeypatch, tmp_path):
    html = """
    <html>
      <a href='http://a'>Item A</a>
      <a href='http://b'>123</a>
      <a href='http://a'>Item A</a>
      <div class='x'><a href='http://d'>Item D</a></div>
    </html>
    """

    monkeypatch.setattr(requests, 'get', lambda url, timeout=10: FakeResponse(html))
    out = tmp_path / 'res.csv'
    exit_code = scrape_collection('http://example', 'a', str(out))

    assert exit_code == 0
    with open(out, newline='', encoding='utf-8') as f:
        rows = list(csv.reader(f))

    assert rows == [
        ['name', 'link'],
        ['Item A', 'http://a'],
        ['Item D', 'http://d'],
    ]


def test_scrape_collection_custom_selector(monkeypatch, tmp_path):
    html = "<div class='x'><a href='http://d'>Item D</a></div>"
    monkeypatch.setattr(requests, 'get', lambda url, timeout=10: FakeResponse(html))
    out = tmp_path / 'res.csv'
    exit_code = scrape_collection('http://example', 'div.x a', str(out))
    assert exit_code == 0
    with open(out, newline='', encoding='utf-8') as f:
        rows = list(csv.reader(f))
    assert rows[-1] == ['Item D', 'http://d']
