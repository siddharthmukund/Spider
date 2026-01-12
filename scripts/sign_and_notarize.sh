#!/usr/bin/env bash
set -euo pipefail

if [ -z "${MACOS_SIGN_ID:-}" ]; then
  echo "MACOS_SIGN_ID not set; skipping codesign/notarize"
  exit 0
fi

APP_DIR=${1:-dist}
APP=$(ls "$APP_DIR" | grep ".app" | head -n1)
if [ -z "$APP" ]; then
  echo "No .app found in $APP_DIR"; exit 1
fi

APP_PATH="$APP_DIR/$APP"

echo "Signing: $APP_PATH with identity $MACOS_SIGN_ID"
# Deep sign and enable runtime flags for hardened runtime
codesign --deep --force --options runtime --sign "$MACOS_SIGN_ID" "$APP_PATH"

# Verify
codesign -v --deep --strict "$APP_PATH" || true
codesign -d --verbose=4 "$APP_PATH" || true

# Notarize (optional)
if [ -n "${NOTARY_PROFILE:-}" ]; then
  echo "Submitting notarization using profile: $NOTARY_PROFILE"
  xcrun notarytool submit --wait --keychain-profile "$NOTARY_PROFILE" "$APP_PATH"
  echo "Stapling notarization ticket"
  xcrun stapler staple "$APP_PATH"
else
  echo "NOTARY_PROFILE not set; skipping notarization"
fi

echo "Sign & notarize complete"