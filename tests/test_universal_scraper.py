import json
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

