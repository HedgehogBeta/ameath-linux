#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="$(PYTHONPATH="$PROJECT_DIR" python3 -c 'from ameath_linux import __version__; print(__version__)')"
OUTPUT_DIR="$PROJECT_DIR/release"
STAGE_DIR="$(mktemp -d)"
PYTHON_DIST="$STAGE_DIR/python-dist"

cleanup() {
    rm -rf -- "$STAGE_DIR"
}
trap cleanup EXIT

mkdir -p "$OUTPUT_DIR"
find "$OUTPUT_DIR" -mindepth 1 -maxdepth 1 -type f -delete
mkdir -p "$PYTHON_DIST"

cd "$PROJECT_DIR"
if python3 -c 'import importlib.util, sys; sys.exit(importlib.util.find_spec("build.__main__") is None)' 2>/dev/null; then
    python3 -m build --outdir "$PYTHON_DIST"
else
    python3 setup.py --quiet sdist --dist-dir "$PYTHON_DIST"
    python3 setup.py --quiet bdist_wheel --dist-dir "$PYTHON_DIST"
fi
cp "$PYTHON_DIST"/*.whl "$PYTHON_DIST"/*.tar.gz "$OUTPUT_DIR/"

PORTABLE_ROOT="$STAGE_DIR/ameath-linux-$VERSION"
mkdir -p "$PORTABLE_ROOT"
cp -a \
    "$PROJECT_DIR/ameath_linux" \
    "$PROJECT_DIR/packaging" \
    "$PORTABLE_ROOT/"
find "$PORTABLE_ROOT" -type d -name __pycache__ -prune -exec rm -rf -- {} +
find "$PORTABLE_ROOT" -type f -name '*.py[co]' -delete
cp \
    "$PROJECT_DIR/main.py" \
    "$PROJECT_DIR/run.sh" \
    "$PROJECT_DIR/install.sh" \
    "$PROJECT_DIR/requirements.txt" \
    "$PROJECT_DIR/pyproject.toml" \
    "$PROJECT_DIR/setup.cfg" \
    "$PROJECT_DIR/setup.py" \
    "$PROJECT_DIR/MANIFEST.in" \
    "$PROJECT_DIR/README.md" \
    "$PROJECT_DIR/LICENSE" \
    "$PROJECT_DIR/SOURCE-LICENSE" \
    "$PROJECT_DIR/CHANGELOG.md" \
    "$PORTABLE_ROOT/"

tar --sort=name --mtime='UTC 2026-01-01' --owner=0 --group=0 --numeric-owner \
    -C "$STAGE_DIR" -cf - "ameath-linux-$VERSION" \
    | gzip -n > "$OUTPUT_DIR/ameath-linux-$VERSION-portable.tar.gz"

"$PROJECT_DIR/scripts/build_deb.sh" "$OUTPUT_DIR"

cd "$OUTPUT_DIR"
sha256sum ./*.whl ./*.tar.gz ./*.deb > SHA256SUMS
printf 'Release artifacts written to %s\n' "$OUTPUT_DIR"
