SEOCrawlerApp — SwiftUI macOS App

Overview
- Lightweight SwiftUI app that uses `SEOCrawlerLib` (local package) to run crawls and show live metrics.

Build & Run
- Open the `swift/SEOCrawlerApp` package in Xcode (File > Open > swift/SEOCrawlerApp) and run the `SEOCrawlerApp` scheme.
- Or build via command line:
  swift build -c release -Xswiftc -target -Xswiftc x86_64-apple-macos10.15

Packaging (local test)
- After `swift build -c release`, the executable exists in `.build/release/SEOCrawlerApp`.
- Create a simple .app bundle: `scripts/create_macos_app.sh .build/release/SEOCrawlerApp` (unsigned)
- Create a DMG: `scripts/make_dmg.sh dist/SEOCrawler.app`

Signing & notarization
- Use `codesign` and `xcrun altool/notarytool` to sign and notarize the DMG. See `docs/release_signing.md` for steps.

Notes
- This is a scaffold. The view model demonstrates how to call into `SEOCrawlerLib` but you'll likely want to expand UI features and threading behavior for production usage.
