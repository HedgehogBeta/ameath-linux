import subprocess
import sys
from pathlib import Path

from ameath_linux import __version__


def test_package_metadata_uses_runtime_version():
    project = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, "setup.py", "--version"],
        cwd=project,
        check=True,
        capture_output=True,
        text=True,
    )
    assert result.stdout.strip() == __version__


def test_changelog_contains_current_version():
    project = Path(__file__).resolve().parents[1]
    changelog = (project / "CHANGELOG.md").read_text(encoding="utf-8")
    assert f"## {__version__}" in changelog
