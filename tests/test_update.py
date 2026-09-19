from ameath_linux.update import is_newer, normalized_version


def test_version_normalization():
    assert normalized_version("v1.2.03-beta") == (1, 2, 3)


def test_version_comparison_pads_components():
    assert is_newer("v1.2.1", "1.2")
    assert not is_newer("v1.2", "1.2.0")

