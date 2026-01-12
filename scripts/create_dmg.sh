#!/usr/bin/env bash
set -euo pipefail

# Create a DMG containing the app and Applications symlink
# Usage: scripts/create_dmg.sh dist "SEO Crawler.app"

ARTIFACTS_DIR=${1:-dist}
APP_NAME=${2}
OUT_DMG=${3:-"${ARTIFACTS_DIR}/${APP_NAME%.app}.dmg"}

if [ -z "$APP_NAME" ]; then
  echo "Usage: create_dmg.sh <artifacts_dir> <AppName.app> [out_dmg]"
  exit 2
fi

if [ ! -d "$ARTIFACTS_DIR/$APP_NAME" ]; then
  echo "App bundle not found: $ARTIFACTS_DIR/$APP_NAME"
  exit 1
fi

TMP_DIR=$(mktemp -d /tmp/packdmg.XXXX)
echo "Using temp dir $TMP_DIR"
mkdir -p "$TMP_DIR/Applications"
cp -R "$ARTIFACTS_DIR/$APP_NAME" "$TMP_DIR/"
ln -s /Applications "$TMP_DIR/Applications"

# Create a compressed read-only DMG
hdiutil create -volname "${APP_NAME%.app}" -srcfolder "$TMP_DIR" -ov -format UDZO "$OUT_DMG"

echo "Created DMG: $OUT_DMG"

# Cleanup
rm -rf "$TMP_DIR"
