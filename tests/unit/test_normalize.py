import importlib.util
import sys
from pathlib import Path

from sonora.matching.normalize import NORMALIZATION_VERSION, base_title, normalize

ROOT = Path(__file__).resolve().parents[2]


def _script_module():
    spec = importlib.util.spec_from_file_location("check_fma_genius", ROOT / "scripts" / "check_fma_genius.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_same_normalization_as_matching_run():
    script = _script_module()
    assert script.NORMALIZATION_VERSION == NORMALIZATION_VERSION
    for value in ["Rock & Roll", "Café  Tacvba!", "HUMBLE.", "Ａｂｃ", "It&#39;s", None, "", "Beyoncé - Halo (Live)"]:
        assert normalize(value) == script.normalize(value)


def test_base_title_only_strips_version_suffixes():
    assert base_title("Halo (Live)") == "halo"
    assert base_title("Halo - 2011 Remaster") == "halo"
    assert base_title("Halo [Acoustic Version]") == "halo"
    assert base_title("Love (Is All Around)") == "love is all around"
    assert base_title("Back - To Black") == "back to black"
    assert base_title("(Live)") == "live"
