import json
import subprocess
import sys
import http.server
import socketserver
import threading
import logging
import requests
from NEW_APPLICATION_EN_DEV import scraper_universel
from NEW_APPLICATION_EN_DEV.scraper_universel import scrap_fiche_generique


def test_scrap_fiche_generique(tmp_path, requests_mock):
    html = (
        "<html>"
        "<h1 class='product-title'>Title</h1>"
        "<span class='product-price'><b>9.99</b></span>"
        "<p class='desc'>Hello</p>"
        "<img class='main-img' src='img.jpg'/>"
        "</html>"
    )
    requests_mock.get('http://example.com', text=html)
    mapping = {
        'title': 'h1.product-title',
        'price': '.product-price b',
        'desc': '.desc',
        'image': 'img.main-img'
    }
    data = scrap_fiche_generique('http://example.com', mapping)
    assert data['title'] == 'Title'
    assert data['price'] == '9.99'
    assert data['desc'] == 'Hello'
    assert data['image'] == 'img.jpg'


def test_mapping_file(tmp_path, requests_mock):
    html = '<html><h1>Title</h1></html>'
    requests_mock.get('http://example.com', text=html)
    mapping = {'title': 'h1'}
    path = tmp_path / 'map.json'
    path.write_text(json.dumps(mapping))
    data = scrap_fiche_generique('http://example.com', mapping_file=str(path))
    assert data['title'] == 'Title'


def test_cli(tmp_path):
    html = '<html><h1>Title</h1></html>'
    mapping = {'title': 'h1'}
    path = tmp_path / 'map.json'
    path.write_text(json.dumps(mapping))

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(html.encode())

    with socketserver.TCPServer(('localhost', 0), Handler) as server:
        port = server.server_address[1]
        thread = threading.Thread(target=server.serve_forever)
        thread.daemon = True
        thread.start()
        try:
            result = subprocess.run(
                [
                    sys.executable,
                    '-m',
                    'NEW_APPLICATION_EN_DEV.scraper_universel',
                    '--url',
                    f'http://localhost:{port}',
                    '--mapping-file',
                    str(path),
                ],
                capture_output=True,
                text=True,
                check=True,
            )
        finally:
            server.shutdown()
            thread.join()

    data = json.loads(result.stdout)
    assert data['title'] == 'Title'


def test_request_error(monkeypatch, caplog):
    def fake_get(url, timeout=10):
        raise requests.exceptions.RequestException('boom')

    monkeypatch.setattr(requests, 'get', fake_get)

    caplog.set_level(logging.ERROR)
    result = scrap_fiche_generique('http://bad', {'title': 'h1'})
    assert result == {}
    assert 'Failed to fetch http://bad' in caplog.text


def test_lxml_parser_used(monkeypatch, requests_mock):
    pytest = __import__('pytest')
    pytest.importorskip('lxml')

    captured = {}
    html = '<html><h1>Title</h1></html>'
    requests_mock.get('http://example.com', text=html)

    real_bs = scraper_universel.BeautifulSoup

    def fake_bs(page, parser):
        captured['parser'] = parser
        return real_bs(page, parser)

    monkeypatch.setattr(scraper_universel, 'BeautifulSoup', fake_bs)
    scrap_fiche_generique('http://example.com', {'title': 'h1'})

    assert captured['parser'] == 'lxml'


def test_html_parser_fallback(monkeypatch, requests_mock):
    captured = {}
    html = '<html><h1>Title</h1></html>'
    requests_mock.get('http://example.com', text=html)

    real_bs = scraper_universel.BeautifulSoup

    def fake_bs(page, parser):
        captured['parser'] = parser
        return real_bs(page, parser)

    monkeypatch.setattr(scraper_universel, 'BeautifulSoup', fake_bs)
    monkeypatch.setattr(scraper_universel, 'html', None)
    scrap_fiche_generique('http://example.com', {'title': 'h1'})

    assert captured['parser'] == 'html.parser'

