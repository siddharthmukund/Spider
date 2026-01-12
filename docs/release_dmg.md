# Creating a macOS DMG for distribution

This document explains how we create a distributable macOS DMG for the application.

Prerequisites:
- Build the `.app` using `scripts/package_mac.sh` (or CI). The resulting `.app` will be placed in `dist/`.
- Optional: codesign and notarize before packaging the DMG.

Create DMG locally:

```bash
# Example: include icon and bundle id, create DMG
ICON=assets/icon.icns BUNDLE_ID=com.example.seo-crawler VERSION=0.1.0 MAKE_DMG=true bash scripts/package_mac.sh
# Alternatively, if the .app is already present:
bash scripts/create_dmg.sh dist "SEO Crawler.app"
```

CI integration:
- The CI will run `scripts/package_mac.sh` and create a DMG when `MAKE_DMG=true` in the job environment.
- The resulting DMG is uploaded as an artifact alongside the `.app`.

Notes:
- For production releases, ensure the app is signed and notarized prior to DMG creation (see `docs/release_signing.md`).
