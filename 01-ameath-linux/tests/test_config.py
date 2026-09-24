from pathlib import Path

from ameath_linux.config import (
    DEFAULT_CONFIG,
    autostart_contents,
    load_config,
    sanitize_config,
    save_config,
    set_auto_startup,
)


def test_invalid_config_falls_back_to_safe_defaults(tmp_path: Path):
    path = tmp_path / "config.json"
    path.write_text('{"scale_index": 999, "click_through": "yes"}', encoding="utf-8")
    config = load_config(path)
    assert config["scale_index"] == DEFAULT_CONFIG["scale_index"]
    assert config["click_through"] is DEFAULT_CONFIG["click_through"]


def test_round_trip_preserves_supported_values(tmp_path: Path):
    path = tmp_path / "config.json"
    config = sanitize_config({"instance_count": 7, "startup_position": "top_right"})
    save_config(config, path)
    loaded = load_config(path)
    assert loaded["instance_count"] == 7
    assert loaded["startup_position"] == "top_right"


def test_linux_autostart_file_can_be_enabled_and_disabled(tmp_path: Path):
    path = tmp_path / "autostart" / "ameath-linux.desktop"
    set_auto_startup(True, path)
    assert "Exec=" in path.read_text(encoding="utf-8")
    set_auto_startup(False, path)
    assert not path.exists()


def test_autostart_quotes_command_parts():
    text = autostart_contents(["/tmp/a path/python", "-m", "ameath_linux"])
    assert "'/tmp/a path/python' -m ameath_linux" in text

