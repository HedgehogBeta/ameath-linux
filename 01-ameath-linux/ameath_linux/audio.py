from __future__ import annotations

import os
import random
import shutil
import signal
import subprocess
from pathlib import Path

from PyQt5 import QtCore

from .paths import MUSIC_DIR, asset_path

try:
    import gi

    gi.require_version("Gst", "1.0")
    from gi.repository import Gst

    Gst.init(None)
except (ImportError, ValueError):  # pragma: no cover - distro dependent
    Gst = None


class _AudioBackend:
    def __init__(self):
        self._volume = 1.0
        self._source: Path | None = None
        self._paused = False
        self._process: subprocess.Popen | None = None
        self._player = Gst.ElementFactory.make("playbin", None) if Gst else None

    @property
    def available(self) -> bool:
        return self._player is not None or shutil.which("gst-play-1.0") is not None

    def set_volume(self, value: float) -> None:
        self._volume = max(0.0, min(1.5, value))
        if self._player is not None:
            self._player.set_property("volume", self._volume)

    def load(self, path: Path, start_seconds: float = 0.0) -> None:
        self.stop()
        self._source = path
        if self._player is not None:
            self._player.set_property("uri", path.resolve().as_uri())
            self._player.set_property("volume", self._volume)
            if start_seconds:
                self._player.set_state(Gst.State.PAUSED)
                self._player.get_state(Gst.CLOCK_TIME_NONE)
                self.seek(start_seconds)
        else:
            self._start_process(start_seconds)

    def _start_process(self, start_seconds: float = 0.0) -> None:
        if not self._source or not shutil.which("gst-play-1.0"):
            return
        command = [
            "gst-play-1.0",
            "--no-interactive",
            "--quiet",
            f"--volume={min(self._volume, 1.0):.3f}",
        ]
        if start_seconds > 0:
            command.append(f"--start-position={start_seconds:.3f}")
        command.append(str(self._source))
        self._process = subprocess.Popen(
            command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )

    def play(self) -> None:
        self._paused = False
        if self._player is not None:
            self._player.set_state(Gst.State.PLAYING)
        elif self._process is None and self._source:
            self._start_process()
        elif self._process and self._process.poll() is None:
            self._process.send_signal(signal.SIGCONT)

    def pause(self) -> None:
        self._paused = True
        if self._player is not None:
            self._player.set_state(Gst.State.PAUSED)
        elif self._process and self._process.poll() is None:
            self._process.send_signal(signal.SIGSTOP)

    def stop(self) -> None:
        self._paused = False
        if self._player is not None:
            self._player.set_state(Gst.State.NULL)
        if self._process and self._process.poll() is None:
            self._process.terminate()
            try:
                self._process.wait(timeout=0.5)
            except subprocess.TimeoutExpired:
                self._process.kill()
        self._process = None

    def seek(self, seconds: float) -> None:
        seconds = max(0.0, seconds)
        if self._player is not None:
            self._player.seek_simple(
                Gst.Format.TIME,
                Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT,
                int(seconds * Gst.SECOND),
            )
        elif self._source:
            was_paused = self._paused
            self.stop()
            self._start_process(seconds)
            if was_paused:
                self.pause()

    def position(self) -> tuple[float, float]:
        if self._player is None:
            return 0.0, 0.0
        ok_pos, position = self._player.query_position(Gst.Format.TIME)
        ok_dur, duration = self._player.query_duration(Gst.Format.TIME)
        return (
            position / Gst.SECOND if ok_pos and position >= 0 else 0.0,
            duration / Gst.SECOND if ok_dur and duration >= 0 else 0.0,
        )

    def poll_finished(self) -> bool:
        if self._player is not None:
            bus = self._player.get_bus()
            message = bus.pop_filtered(Gst.MessageType.EOS | Gst.MessageType.ERROR)
            return message is not None
        return bool(self._process and self._process.poll() is not None)


class VoicePlayer:
    def __init__(self):
        self.enabled = True
        self.volume = 100
        self._backend = _AudioBackend()
        self._files = sorted(asset_path("sound", "voice").glob("*.wav"))
        self._last: Path | None = None

    def configure(self, enabled: bool, volume: int) -> None:
        self.enabled = enabled
        self.volume = max(0, min(150, int(volume)))
        self._backend.set_volume(self.volume / 100)
        if not enabled:
            self._backend.stop()

    def play_random(self) -> None:
        if not self.enabled or not self._files or not self._backend.available:
            return
        choices = [item for item in self._files if item != self._last] or self._files
        self._last = random.choice(choices)
        self._backend.load(self._last)
        self._backend.play()

    def stop(self) -> None:
        self._backend.stop()


class MusicPlayer(QtCore.QObject):
    state_changed = QtCore.pyqtSignal(bool, bool)
    track_changed = QtCore.pyqtSignal(str)
    position_changed = QtCore.pyqtSignal(float, float)
    files_changed = QtCore.pyqtSignal()

    def __init__(self, volume: int = 100):
        super().__init__()
        self.backend = _AudioBackend()
        self.files: list[Path] = []
        self.current_index = -1
        self.playing = False
        self.paused = False
        self.set_volume(volume)
        self.ensure_music_folder()
        self.refresh()
        self._poll = QtCore.QTimer(self)
        self._poll.setInterval(250)
        self._poll.timeout.connect(self._poll_backend)
        self._poll.start()

    def ensure_music_folder(self) -> None:
        MUSIC_DIR.mkdir(parents=True, exist_ok=True)
        bundled = asset_path("sound", "music")
        for source in bundled.glob("*.mp3"):
            target = MUSIC_DIR / source.name
            if not target.exists():
                shutil.copy2(source, target)

    def refresh(self) -> None:
        suffixes = {".mp3", ".wav", ".flac", ".ogg", ".m4a"}
        current = self.current_path
        self.files = sorted(
            (p for p in MUSIC_DIR.iterdir() if p.suffix.lower() in suffixes),
            key=lambda p: p.name.casefold(),
        )
        if current in self.files:
            self.current_index = self.files.index(current)
        elif self.files and self.current_index < 0:
            self.current_index = 0
        elif not self.files:
            self.current_index = -1
        self.files_changed.emit()

    @property
    def current_path(self) -> Path | None:
        if 0 <= self.current_index < len(self.files):
            return self.files[self.current_index]
        return None

    def set_volume(self, volume: int) -> None:
        self.volume = max(0, min(100, int(volume)))
        self.backend.set_volume(self.volume / 100)

    def play(self, index: int | None = None) -> None:
        if not self.files:
            return
        if index is not None:
            self.current_index = index % len(self.files)
        if self.current_index < 0:
            self.current_index = random.randrange(len(self.files))
        path = self.current_path
        if path is None:
            return
        self.backend.load(path)
        self.backend.play()
        self.playing = True
        self.paused = False
        self.track_changed.emit(path.name)
        self.state_changed.emit(True, False)

    def toggle(self) -> None:
        if not self.playing:
            self.play()
        elif self.paused:
            self.backend.play()
            self.paused = False
            self.state_changed.emit(True, False)
        else:
            self.backend.pause()
            self.paused = True
            self.state_changed.emit(True, True)

    def stop(self) -> None:
        self.backend.stop()
        self.playing = False
        self.paused = False
        self.state_changed.emit(False, False)

    def next(self) -> None:
        if self.files:
            self.play((self.current_index + 1) % len(self.files))

    def previous(self) -> None:
        if self.files:
            self.play((self.current_index - 1) % len(self.files))

    def seek(self, seconds: float) -> None:
        self.backend.seek(seconds)

    def import_files(self, paths: list[str]) -> None:
        MUSIC_DIR.mkdir(parents=True, exist_ok=True)
        for raw in paths:
            source = Path(raw)
            if not source.is_file():
                continue
            target = MUSIC_DIR / source.name
            counter = 1
            while target.exists() and not os.path.samefile(source, target):
                target = MUSIC_DIR / f"{source.stem}_{counter}{source.suffix}"
                counter += 1
            if not target.exists():
                shutil.copy2(source, target)
        self.refresh()

    def _poll_backend(self) -> None:
        if not self.playing:
            return
        if self.backend.poll_finished():
            self.next()
            return
        position, duration = self.backend.position()
        self.position_changed.emit(position, duration)

