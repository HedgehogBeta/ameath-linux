from __future__ import annotations

import json
import shlex
from copy import deepcopy
from pathlib import Path
from typing import Any

from .constants import DEFAULT_SCALE_INDEX, DEFAULT_TRANSPARENCY_INDEX
from .paths import AUTOSTART_FILE, CONFIG_FILE, launch_command


DEFAULT_CONFIG: dict[str, Any] = {
    "total_screen": True,
    "screen_index": 0,
    "scale_index": DEFAULT_SCALE_INDEX,
    "window_snap": True,
    "transparency_index": DEFAULT_TRANSPARENCY_INDEX,
    "auto_startup": False,
    "click_through": False,
    "follow_mouse": False,
    "display_priority": 1,
    "wander_idle_stay_mode": 2,
    "instance_count": 1,
    "skip_updates": False,
    "skip_version": None,
    "voice_enabled": True,
    "voice_volume": 100,
    "music_enabled": True,
    "music_volume": 100,
    "startup_position": "random",
    "start_paused": False,
}


def _int(value: Any, default: int, low: int, high: int) -> int:
    try:
        value = int(value)
    except (TypeError, ValueError):
        return default
    return value if low <= value <= high else default


def sanitize_config(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return deepcopy(DEFAULT_CONFIG)
    result = deepcopy(DEFAULT_CONFIG)
    for key in (
        "total_screen",
        "window_snap",
        "auto_startup",
        "click_through",
        "follow_mouse",
        "skip_updates",
        "voice_enabled",
        "music_enabled",
        "start_paused",
    ):
        if isinstance(value.get(key), bool):
            result[key] = value[key]
    limits = {
        "screen_index": (0, 64),
        "scale_index": (0, 19),
        "transparency_index": (0, 9),
        "display_priority": (1, 3),
        "wander_idle_stay_mode": (0, 2),
        "instance_count": (1, 80),
        "voice_volume": (0, 150),
        "music_volume": (0, 100),
    }
    for key, (low, high) in limits.items():
        result[key] = _int(value.get(key), result[key], low, high)
    if value.get("startup_position") in {
        "random",
        "bottom_right",
        "bottom_left",
        "top_right",
        "top_left",
        "center",
    }:
        result["startup_position"] = value["startup_position"]
    if value.get("skip_version") is None or isinstance(value.get("skip_version"), str):
        result["skip_version"] = value.get("skip_version")
    return result


def load_config(path: Path = CONFIG_FILE) -> dict[str, Any]:
    try:
        return sanitize_config(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, ValueError, TypeError):
        return deepcopy(DEFAULT_CONFIG)


def save_config(config: dict[str, Any], path: Path = CONFIG_FILE) -> None:
    clean = sanitize_config(config)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(clean, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(path)


def autostart_contents(command: list[str] | None = None) -> str:
    command = command or launch_command()
    executable = " ".join(shlex.quote(part) for part in command)
    return "\n".join(
        [
            "[Desktop Entry]",
            "Type=Application",
            "Name=Ameath Desktop Pet",
            f"Exec={executable}",
            "Icon=ameath-linux",
            "Terminal=false",
            "X-GNOME-Autostart-enabled=true",
            "StartupNotify=false",
            "",
        ]
    )


def set_auto_startup(enabled: bool, path: Path = AUTOSTART_FILE) -> None:
    if enabled:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(autostart_contents(), encoding="utf-8")
    else:
        try:
            path.unlink()
        except FileNotFoundError:
            pass


def is_auto_startup_enabled(path: Path = AUTOSTART_FILE) -> bool:
    return path.is_file()

