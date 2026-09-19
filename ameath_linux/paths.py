from __future__ import annotations

import os
import sys
from pathlib import Path


PACKAGE_DIR = Path(__file__).resolve().parent
ASSET_DIR = PACKAGE_DIR / "assets"


def xdg_dir(variable: str, fallback: Path) -> Path:
    raw = os.environ.get(variable)
    return Path(raw).expanduser() if raw else fallback


CONFIG_DIR = Path(
    os.environ.get(
        "AMEATH_CONFIG_DIR",
        xdg_dir("XDG_CONFIG_HOME", Path.home() / ".config") / "ameath-linux",
    )
).expanduser()
CONFIG_FILE = CONFIG_DIR / "config.json"
AUTOSTART_FILE = Path(
    os.environ.get(
        "AMEATH_AUTOSTART_FILE",
        xdg_dir("XDG_CONFIG_HOME", Path.home() / ".config")
        / "autostart"
        / "ameath-linux.desktop",
    )
).expanduser()
MUSIC_DIR = Path(os.environ.get("AMEATH_MUSIC_DIR", Path.home() / "ameath_songs")).expanduser()


def asset_path(*parts: str) -> Path:
    return ASSET_DIR.joinpath(*parts)


def launch_command() -> list[str]:
    if getattr(sys, "frozen", False):
        return [str(Path(sys.executable).resolve())]
    return [sys.executable, "-m", "ameath_linux"]
