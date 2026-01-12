#!/usr/bin/env bash
set -euo pipefail

# Basic PyInstaller packaging script for macOS
# Usage: bash scripts/package_mac.sh

APP_NAME="SEO Crawler"
ENTRY_POINT="run_gui.py"

# Clean
rm -rf dist build "${APP_NAME}.spec"

# Prefer virtualenv python if present
if [ -x ".venv/bin/python" ]; then
  PYTHON=.venv/bin/python
else
  PYTHON=${PYTHON:-python3}
fi
# Build using Python helper to keep logic consistent
$PYTHON scripts/package_mac.py "${ENTRY_POINT}" "${APP_NAME}" "${ICON:-None}" "${BUNDLE_ID:-None}" "${VERSION:-None}"

echo "Packaging complete. Check ./dist/${APP_NAME}.app"

if [ "${MAKE_DMG:-false}" = "true" ]; then
  echo "Creating DMG..."
  bash scripts/create_dmg.sh dist "${APP_NAME}.app"
fi