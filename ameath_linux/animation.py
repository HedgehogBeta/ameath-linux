from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PyQt5 import QtCore, QtGui


@dataclass(frozen=True)
class Animation:
    frames: tuple[QtGui.QPixmap, ...]
    delays: tuple[int, ...]

    def __bool__(self) -> bool:
        return bool(self.frames)


def load_animation(path: Path, scale: float, mirrored: bool = False) -> Animation:
    reader = QtGui.QImageReader(str(path))
    reader.setAutoTransform(True)
    frames: list[QtGui.QPixmap] = []
    delays: list[int] = []
    frame_count = max(1, reader.imageCount())
    for _ in range(frame_count):
        image = reader.read()
        if image.isNull():
            break
        if mirrored:
            image = image.mirrored(True, False)
        if scale != 1.0:
            image = image.scaled(
                max(1, round(image.width() * scale)),
                max(1, round(image.height() * scale)),
                QtCore.Qt.KeepAspectRatio,
                QtCore.Qt.SmoothTransformation,
            )
        frames.append(QtGui.QPixmap.fromImage(image))
        delays.append(max(30, reader.nextImageDelay() or 100))
    return Animation(tuple(frames), tuple(delays))


class AssetBank:
    def __init__(self, gif_dir: Path):
        self.gif_dir = gif_dir
        self._cache: dict[tuple[str, float, bool], Animation] = {}

    def animation(self, name: str, scale: float, mirrored: bool = False) -> Animation:
        key = (name, scale, mirrored)
        if key not in self._cache:
            self._cache[key] = load_animation(self.gif_dir / name, scale, mirrored)
        return self._cache[key]

    def retain_scale(self, scale: float) -> None:
        self._cache = {
            key: animation for key, animation in self._cache.items() if key[1] == scale
        }
