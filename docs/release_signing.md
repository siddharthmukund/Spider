# macOS Code Signing & Notarization (Draft)

This document outlines an optional workflow for signing and notarizing the macOS `.app` produced by `scripts/package_mac.sh` using `codesign` and Apple's `notarytool`/`altool`.

> WARNING: This requires an Apple Developer account and access to a signing certificate (Developer ID Application) and an App Store Connect API key or Apple ID credentials. Do NOT store secrets in the repo; use GitHub Actions secrets.

Overview
- Signing:
  - Use `codesign --deep --force --options runtime --sign "$CERT_ID" "dist/MyApp.app"` to sign the app bundle.
  - Verify with `codesign -v --deep --strict "dist/MyApp.app"` and `codesign -d --verbose=4 "dist/MyApp.app"`.

- Notarization (recommended for distributed builds):
  - Use `xcrun notarytool submit --wait --keychain-profile <profile> "dist/MyApp.app"` (preferred) or the older `altool`.
  - Once notarized, staple the ticket: `xcrun stapler staple "dist/MyApp.app"`.

Automation notes (CI)
- Store signing identity and API key data in GitHub Secrets: `MACOS_SIGN_ID`, `NOTARY_PROFILE`.
- Add a CI step that is gated by the presence of those secrets (skip if not set).
- The signing/notarization step should run after the packaging step and before uploading artifacts.

Helper script
- `scripts/sign_and_notarize.sh` will be provided as a convenience wrapper that will:
  - Exit early if `MACOS_SIGN_ID` is not set.
  - Run `codesign` with the appropriate flags.
  - Optionally call `xcrun notarytool` if `NOTARY_PROFILE` is present.

Security considerations
- Use ephemeral credentials or GitHub Actions' secret store.
- Avoid printing sensitive values in CI logs.

This is a draft; I can wire the optional CI steps and helper scripts into the pipeline if you want me to proceed.