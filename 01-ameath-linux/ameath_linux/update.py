from __future__ import annotations

import json
import re
import urllib.request
from dataclasses import dataclass

from .constants import GITHUB_RELEASE_API, GITHUB_RELEASES_URL


@dataclass(frozen=True)
class ReleaseInfo:
    version: str
    notes: str
    page_url: str
    asset_url: str | None = None
    asset_name: str | None = None


def normalized_version(value: str) -> tuple[int, ...]:
    numbers = re.findall(r"\d+", value)
    return tuple(int(item) for item in numbers) or (0,)


def is_newer(candidate: str, current: str) -> bool:
    left = normalized_version(candidate)
    right = normalized_version(current)
    length = max(len(left), len(right))
    return left + (0,) * (length - len(left)) > right + (0,) * (length - len(right))


def check_latest(timeout: float = 8.0) -> ReleaseInfo:
    request = urllib.request.Request(
        GITHUB_RELEASE_API,
        headers={"User-Agent": "Ameath-Linux/1.1 (+desktop-pet)"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = json.load(response)
    if not isinstance(payload, list):
        raise ValueError("GitHub 发布列表格式无效")
    releases = (
        item for item in payload
        if isinstance(item, dict)
        and not item.get("draft")
        and not item.get("prerelease")
        and re.fullmatch(
            r"(?:ameath-linux-)?v\d+(?:\.\d+)+",
            str(item.get("tag_name") or ""),
        )
    )
    release = max(
        releases,
        key=lambda item: normalized_version(str(item["tag_name"])),
        default=None,
    )
    if release is None:
        raise ValueError("未找到 Ameath Linux 的正式版本")
    assets = release.get("assets") or []
    preferred = None
    for item in assets:
        name = str(item.get("name", ""))
        lower = name.lower()
        if lower.endswith((".appimage", ".tar.gz", ".zip")) and (
            "linux" in lower or "ameath" in lower
        ):
            preferred = item
            if lower.endswith(".appimage"):
                break
    return ReleaseInfo(
        version=str(release["tag_name"]).removeprefix("ameath-linux-"),
        notes=str(release.get("body") or "暂无发布说明"),
        page_url=str(release.get("html_url") or GITHUB_RELEASES_URL),
        asset_url=(preferred or {}).get("browser_download_url"),
        asset_name=(preferred or {}).get("name"),
    )
