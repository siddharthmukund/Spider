#!/usr/bin/env bash
set -euo pipefail

APP_PATH=$1
OUT_DMG=${2:-"seo_crawler.dmg"}

if [ ! -d "$APP_PATH" ]; then
  echo "App path not found: $APP_PATH"
  exit 1
fi

hdiutil create -volname "SEO Crawler" -srcfolder "$APP_PATH" -ov -format UDZO "$OUT_DMG"

echo "Created dmg: $OUT_DMG"
