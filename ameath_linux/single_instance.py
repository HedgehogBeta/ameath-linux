from __future__ import annotations

import fcntl
import os
import signal
import tempfile
from pathlib import Path
from typing import TextIO


class InstanceLock:
    def __init__(self, path: Path | None = None):
        runtime_dir = Path(os.environ.get("XDG_RUNTIME_DIR", tempfile.gettempdir()))
        override = os.environ.get("AMEATH_INSTANCE_LOCK")
        self.path = path or (
            Path(override)
            if override
            else runtime_dir / f"ameath-linux-{os.getuid()}.lock"
        )
        self._file: TextIO | None = None

    def acquire(self) -> bool:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        handle = self.path.open("a+", encoding="ascii")
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            handle.close()
            return False
        handle.seek(0)
        handle.truncate()
        handle.write(str(os.getpid()))
        handle.flush()
        self._file = handle
        return True

    def notify_running(self, command: str) -> bool:
        try:
            pid = int(self.path.read_text(encoding="ascii").strip())
            requested_signal = signal.SIGTERM if command == "quit" else signal.SIGUSR1
            os.kill(pid, requested_signal)
            return True
        except (OSError, ValueError):
            return False

    def release(self) -> None:
        if self._file is None:
            return
        try:
            fcntl.flock(self._file.fileno(), fcntl.LOCK_UN)
        finally:
            self._file.close()
            self._file = None
        try:
            self.path.unlink()
        except FileNotFoundError:
            pass
