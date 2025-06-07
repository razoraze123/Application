import importlib.util
import pytest

if importlib.util.find_spec("flake8") is not None:
    from flake8.api import legacy as flake8
else:  # pragma: no cover - optional dependency
    flake8 = None


def test_flake8():
    if flake8 is None:
        pytest.skip("flake8 non disponible")
    style = flake8.get_style_guide(max_line_length=79)
    report = style.check_files(["."])
    assert report.total_errors == 0, "flake8 found violations"
