from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class WindowInfo:
    window_id: str
    x: int
    y: int
    width: int
    height: int
    title: str = ""


def is_wayland() -> bool:
    return bool(os.environ.get("WAYLAND_DISPLAY")) or os.environ.get(
        "XDG_SESSION_TYPE", ""
    ).lower() == "wayland"


def _run(*args: str) -> str:
    try:
        return subprocess.check_output(
            args, text=True, stderr=subprocess.DEVNULL, timeout=0.8
        )
    except (OSError, subprocess.SubprocessError):
        return ""


def active_window() -> WindowInfo | None:
    if is_wayland():
        return None
    root = _run("xprop", "-root", "_NET_ACTIVE_WINDOW")
    match = re.search(r"window id # (0x[0-9a-fA-F]+)", root)
    if not match or match.group(1) == "0x0":
        return None
    window_id = match.group(1)
    info = _run("xwininfo", "-id", window_id)
    fields = {}
    for label in ("Absolute upper-left X", "Absolute upper-left Y", "Width", "Height"):
        found = re.search(rf"{re.escape(label)}:\s*(-?\d+)", info)
        if not found:
            return None
        fields[label] = int(found.group(1))
    title_out = _run("xprop", "-id", window_id, "_NET_WM_NAME", "WM_NAME")
    title_match = re.search(r'=\s*"(.*?)"', title_out)
    return WindowInfo(
        window_id,
        fields["Absolute upper-left X"],
        fields["Absolute upper-left Y"],
        fields["Width"],
        fields["Height"],
        title_match.group(1) if title_match else "",
    )


def active_window_is_fullscreen(screen_rects: list[tuple[int, int, int, int]]) -> bool:
    info = active_window()
    if info is None:
        return False
    states = _run("xprop", "-id", info.window_id, "_NET_WM_STATE")
    if "_NET_WM_STATE_FULLSCREEN" in states:
        return True
    for x, y, width, height in screen_rects:
        if (
            info.x <= x + 2
            and info.y <= y + 2
            and info.width >= width - 4
            and info.height >= height - 4
        ):
            return True
    return False


def open_path(path: Path) -> None:
    try:
        subprocess.Popen(
            ["xdg-open", str(path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
    except OSError:
        pass

