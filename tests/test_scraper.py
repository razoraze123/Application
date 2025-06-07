import pytest

from core import scraper as scr


class FakeDriver:
    def __init__(self):
        self.visited = []
        self.page_source = (
            "<html><h1>Title</h1><div id='product_description'>"
            "Desc</div></html>"
        )
        self.quit_called = False

    def get(self, url):
        self.visited.append(url)

    def find_element(self, *args, **kwargs):
        class E:
            text = "Test Name"
        return E()

    def execute_script(self, *a, **k):
        pass

    def quit(self):
        self.quit_called = True


class FakeDataFrame(list):
    def to_excel(self, path, index=False):
        self.saved_path = path


class FakePandas:
    def __init__(self):
        self.captured = None
        self.df = None

    def DataFrame(self, data, **kwargs):
        self.captured = data
        self.df = FakeDataFrame()
        return self.df


@pytest.fixture
def fake_pandas(monkeypatch):
    fp = FakePandas()
    monkeypatch.setattr(scr, "pd", fp)
    return fp


def test_scrap_produits_par_ids(monkeypatch, tmp_path, fake_pandas):
    driver = FakeDriver()
    monkeypatch.setattr(scr, "_get_driver", lambda headless=False: driver)
    monkeypatch.setattr(scr, "_parse_price", lambda d: "9.99")
    monkeypatch.setattr(scr, "_get_variant_names", lambda d: ["Red", "Blue"])
    monkeypatch.setattr("time.sleep", lambda x: None)
    id_map = {"A1": "http://example.com"}
    exit_code = scr.scrap_produits_par_ids(id_map, ["A1"], str(tmp_path))

    assert exit_code == 0
    assert driver.visited == ["http://example.com"]
    assert driver.quit_called
    assert isinstance(fake_pandas.captured, list)
    assert fake_pandas.captured[0]["Type"] == "variable"
    assert fake_pandas.df.saved_path.endswith("woocommerce_mix.xlsx")


def test_scrap_fiches_concurrents(monkeypatch, tmp_path, fake_pandas):
    driver = FakeDriver()
    monkeypatch.setattr(scr, "_get_driver", lambda headless=False: driver)
    monkeypatch.setattr(scr, "_extract_title", lambda soup: "My Title")
    monkeypatch.setattr(
        scr, "_find_description_div", lambda soup: soup.find("div")
    )
    monkeypatch.setattr(scr, "_convert_links", lambda div: None)
    monkeypatch.setattr("time.sleep", lambda x: None)
    id_map = {"A1": "http://example.com"}
    exit_code = scr.scrap_fiches_concurrents(id_map, ["A1"], str(tmp_path))

    assert exit_code == 0
    assert driver.visited == ["http://example.com"]
    assert driver.quit_called
    fc_dir = tmp_path / "fiches_concurrents"
    assert fc_dir.exists()
    assert isinstance(fake_pandas.captured, list)
