from pathlib import Path


MAIN_SOURCE = Path(__file__).resolve().parents[1] / 'src' / 'main.py'


def read_main_source():
    return MAIN_SOURCE.read_text(encoding='utf-8')


def test_preview_boundary_script_is_not_broken_by_nested_script_tag():
    source = read_main_source()

    assert 'function getPointerCoefficient(event) {\n      <script>' not in source
    assert source.count('const feedToggle = document.getElementById') == 1
    assert 'function fetchCameraStatus()' in source
    assert 'function normalizeRectangle(rectangle)' in source
    assert 'function renderCountingBoundary()' in source


def test_preview_boundary_initial_visibility_uses_counting_mode():
    source = read_main_source()

    assert 'id="detection-line" class="{% if counting_mode != \'line\' %}hidden-overlay{% endif %}"' in source
    assert 'id="detection-rectangle" class="{% if counting_mode != \'rectangle\' %}hidden-overlay{% endif %}"' in source
