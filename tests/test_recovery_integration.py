import os
import subprocess
import sys
import time
from pathlib import Path


def test_second_process_shows_then_quits_the_first_process(tmp_path: Path):
    project = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env.update(
        {
            "QT_QPA_PLATFORM": "offscreen",
            "AMEATH_CONFIG_DIR": str(tmp_path / "config"),
            "AMEATH_MUSIC_DIR": str(tmp_path / "music"),
            "AMEATH_AUTOSTART_FILE": str(tmp_path / "autostart.desktop"),
            "AMEATH_INSTANCE_LOCK": str(tmp_path / "instance.lock"),
        }
    )
    primary = subprocess.Popen(
        [sys.executable, "main.py"],
        cwd=project,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        deadline = time.monotonic() + 5
        while not Path(env["AMEATH_INSTANCE_LOCK"]).exists():
            assert primary.poll() is None
            assert time.monotonic() < deadline
            time.sleep(0.02)

        shown = subprocess.run(
            [sys.executable, "main.py"], cwd=project, env=env, timeout=5
        )
        assert shown.returncode == 0
        assert primary.poll() is None

        stopped = subprocess.run(
            [sys.executable, "main.py", "--quit"], cwd=project, env=env, timeout=5
        )
        assert stopped.returncode == 0
        assert primary.wait(timeout=5) == 0
    finally:
        if primary.poll() is None:
            primary.terminate()
            primary.wait(timeout=5)

