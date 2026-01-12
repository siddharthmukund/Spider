# Spider (SEO Crawler & GUI)

Spider is an SEO crawler and audit tool for discovering site issues and producing CSV/JSON reports.

This project contains an enterprise-grade SEO crawler and a PySide6 GUI.

Quick start (developer):

- Create and activate your venv, then install:
  ```bash
  pip install -r requirements.txt
  ```

- Run the GUI:
  ```bash
  python run_gui.py
  ```

Packaging (macOS):

- A simple packaging script is provided at `scripts/package_mac.sh` or `scripts/package_mac.py`.
- A verification helper is included at `scripts/verify_macos_artifact.py` which will:
  - Find the first `.app` in a given artifacts directory,
  - Validate `Contents/Info.plist` exists,
  - Perform a short headless smoke-launch (`QT_QPA_PLATFORM=offscreen`) and report failures.
- The CI contains a `package-macos` job that builds the macOS app using PyInstaller, runs the verification script, and uploads artifacts.
- If you prefer to run locally on macOS, run:
  ```bash
  bash scripts/package_mac.sh
  # then verify locally
  python3 scripts/verify_macos_artifact.py dist
  ```
- Notes: Code signing and notarization are platform-specific; the CI currently performs an ad-hoc codesign during the packaging step on macOS. For production releases, consider adding proper signing with a Team ID and notarization steps. See `docs/release_signing.md` for a draft of signing/notarization steps and a helper script (`scripts/sign_and_notarize.sh`).

Testing & CI:

- Tests use `pytest` + `pytest-qt`. The CI runs all tests headless using `xvfb` and additionally runs viewer E2E tests.

Accessibility & shortcuts:

- The GUI contains accessibility names and keyboard shortcuts for common actions (start/stop, view report, navigation).

Swift rewrite:

- A Swift rewrite prototype lives in `swift/` which contains `SEOCrawlerLib` with a basic `HTTPFetcher` and `HTMLParser` and a minimal `seocrawler-cli` demonstration. Run `swift test` in `swift/` to execute unit tests.

## Quick Start

Create and activate a Python virtual environment, then install dependencies and run tests:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest
```

## Contributing

Contributions are welcome — open an issue or a PR. Please keep changes small and include tests for new behavior.

## License

Add your project license here (e.g., MIT).
