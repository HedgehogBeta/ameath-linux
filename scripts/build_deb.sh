#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
OUTPUT_DIR="${1:-$PROJECT_DIR/release}"
VERSION="$(PYTHONPATH="$PROJECT_DIR" python3 -c 'from ameath_linux import __version__; print(__version__)')"
PACKAGE_FILE="$OUTPUT_DIR/ameath-linux_${VERSION}_all.deb"
STAGE_DIR="$(mktemp -d)"

cleanup() {
    rm -rf -- "$STAGE_DIR"
}
trap cleanup EXIT

mkdir -p \
    "$STAGE_DIR/DEBIAN" \
    "$STAGE_DIR/opt/ameath-linux" \
    "$STAGE_DIR/usr/bin" \
    "$STAGE_DIR/usr/share/applications" \
    "$STAGE_DIR/usr/share/doc/ameath-linux" \
    "$STAGE_DIR/usr/share/icons/hicolor/256x256/apps" \
    "$OUTPUT_DIR"

cp -a "$PROJECT_DIR/ameath_linux" "$STAGE_DIR/opt/ameath-linux/"
find "$STAGE_DIR/opt/ameath-linux" -type d -name __pycache__ -prune -exec rm -rf -- {} +
find "$STAGE_DIR/opt/ameath-linux" -type f -name '*.py[co]' -delete
install -m 0644 "$PROJECT_DIR/main.py" "$STAGE_DIR/opt/ameath-linux/main.py"
install -m 0644 "$PROJECT_DIR/packaging/ameath-linux.desktop" \
    "$STAGE_DIR/usr/share/applications/ameath-linux.desktop"
install -m 0644 "$PROJECT_DIR/ameath_linux/assets/gifs/ameath_content.png" \
    "$STAGE_DIR/usr/share/icons/hicolor/256x256/apps/ameath-linux.png"
install -m 0644 "$PROJECT_DIR/LICENSE" "$STAGE_DIR/usr/share/doc/ameath-linux/copyright"
install -m 0644 "$PROJECT_DIR/SOURCE-LICENSE" \
    "$STAGE_DIR/usr/share/doc/ameath-linux/SOURCE-LICENSE"
install -m 0644 "$PROJECT_DIR/CHANGELOG.md" \
    "$STAGE_DIR/usr/share/doc/ameath-linux/changelog.md"

cat > "$STAGE_DIR/usr/bin/ameath-linux" <<'WRAPPER'
#!/usr/bin/env bash
exec python3 /opt/ameath-linux/main.py "$@"
WRAPPER
chmod 0755 "$STAGE_DIR/usr/bin/ameath-linux"

INSTALLED_SIZE="$(du -sk "$STAGE_DIR/opt/ameath-linux" | cut -f1)"
cat > "$STAGE_DIR/DEBIAN/control" <<CONTROL
Package: ameath-linux
Version: $VERSION
Section: games
Priority: optional
Architecture: all
Installed-Size: $INSTALLED_SIZE
Depends: python3 (>= 3.10), python3-pyqt5, python3-gi, gir1.2-gstreamer-1.0, gstreamer1.0-plugins-good, x11-utils
Maintainer: HedgehogBeta <236519605+HedgehogBeta@users.noreply.github.com>
Homepage: https://github.com/HedgehogBeta/ameath-linux
Description: Ameath animated desktop pet for Linux
 An unofficial Linux port of Ameath with desktop wandering, tray controls,
 multiple pets, audio playback, startup integration and X11-aware behavior.
CONTROL

dpkg-deb --build --root-owner-group "$STAGE_DIR" "$PACKAGE_FILE"
printf '%s\n' "$PACKAGE_FILE"
