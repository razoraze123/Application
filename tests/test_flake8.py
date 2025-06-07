from flake8.api import legacy as flake8


def test_flake8():
    style = flake8.get_style_guide(max_line_length=79)
    report = style.check_files(["."])
    assert report.total_errors == 0, "flake8 found violations"
