#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="${HOME}/.local/bin"
APP_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
ICON_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/icons/hicolor/256x256/apps"

if ! python3 -c 'import PyQt5' 2>/dev/null; then
    echo "未找到 PyQt5。Ubuntu/Debian 请先运行：sudo apt install python3-pyqt5" >&2
    exit 1
fi

python3 -m pip install --user --no-deps --no-build-isolation --upgrade "$PROJECT_DIR"
mkdir -p "$BIN_DIR" "$APP_DIR" "$ICON_DIR"
install -m 0644 "$PROJECT_DIR/packaging/ameath-linux.desktop" "$APP_DIR/ameath-linux.desktop"
install -m 0644 "$PROJECT_DIR/ameath_linux/assets/gifs/ameath_content.png" "$ICON_DIR/ameath-linux.png"

echo "Ameath Linux 已安装。运行：$BIN_DIR/ameath-linux"
