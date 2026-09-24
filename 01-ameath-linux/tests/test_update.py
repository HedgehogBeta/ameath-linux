import io
import json

from ameath_linux import update
from ameath_linux.update import is_newer, normalized_version


def test_version_normalization():
    assert normalized_version("v1.2.03-beta") == (1, 2, 3)


def test_version_comparison_pads_components():
    assert is_newer("v1.2.1", "1.2")
    assert not is_newer("v1.2", "1.2.0")


def test_update_check_selects_latest_ameath_release(monkeypatch):
    releases = [
        {"tag_name": "other-project-v9.0.0"},
        {
            "tag_name": "ameath-linux-v1.1.9.4",
            "body": "新版",
            "html_url": "https://example.com/ameath",
            "assets": [],
        },
        {"tag_name": "ameath-linux-v1.1.9.5", "prerelease": True},
        {"tag_name": "v1.1.9.3", "assets": []},
    ]
    monkeypatch.setattr(
        update.urllib.request,
        "urlopen",
        lambda *_args, **_kwargs: io.BytesIO(json.dumps(releases).encode()),
    )

    result = update.check_latest()

    assert result.version == "v1.1.9.4"
    assert result.notes == "新版"
    assert result.page_url == "https://example.com/ameath"
