import os
import urllib.request

from core.image_scraper import ImageScraper


class FakeImage:
    def __init__(self, src):
        self._src = src

    def get_attribute(self, name):
        return self._src if name == "src" else None


class FakeDriver:
    def __init__(self):
        self.visited = []
        self.title = "Test Product | Shop"
        self.quit_called = False

    def get(self, url):
        self.visited.append(url)

    def find_elements(self, *args, **kwargs):
        return [
            FakeImage("http://example.com/a.webp"),
            FakeImage("http://example.com/b.webp"),
        ]

    def quit(self):
        self.quit_called = True


def test_scrape_images(monkeypatch, tmp_path):
    driver = FakeDriver()

    scraper = ImageScraper(root_folder=str(tmp_path))

    monkeypatch.setattr(ImageScraper, "setup_driver", lambda self: driver)
    monkeypatch.setattr(
        ImageScraper,
        "get_image_elements",
        lambda self: driver.find_elements(),
    )
    monkeypatch.setattr(
        urllib.request,
        "urlretrieve",
        lambda url, fp: open(fp, "wb").write(b"data"),
    )
    scraper.driver = driver
    monkeypatch.setattr("time.sleep", lambda x: None)

    exit_code = scraper.scrape_images(["http://product"])

    assert exit_code == 0
    assert driver.visited == ["http://product"]
    assert driver.quit_called
    saved_dir = tmp_path / "test-product"
    assert saved_dir.exists()
    files = sorted(os.listdir(saved_dir))
    assert files == ["img_0.webp", "img_1.webp"]
