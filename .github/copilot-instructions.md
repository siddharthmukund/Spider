# GitHub Copilot instructions for contributors (AI agents)

Purpose
- Short, practical tips for an AI agent to get productive in this repo quickly. Focus on where behavior lives, what tests expect, and how to run the project locally/CI.

Big picture ✨
- Core crawler logic: `Crawler.py` exposes `AdvancedSEOCrawler` which performs the crawl, writes reporting files (`<out>/seo_report.json`, `<out>/seo_data.csv`) and uses `DatabaseManager` (SQLite `crawl_data.db`) and callbacks (`progress_callback`, `metrics_callback`).
- GUIs: `run_gui.py` starts a PySide6 desktop GUI (code in `gui/`) — `gui/Worker` integrates with `AdvancedSEOCrawler` in a background thread.
- Web API: `webapp/` contains a FastAPI service (`webapp/main.py`) providing `POST /start`, SSE (`/events/{id}`) and WebSocket (`/ws/{id}`) endpoints; it persists task state to `webapp/data/tasks.json` and `webapp/data/<task_id>/events.log` via `webapp/store.py`.
- Optional distributed mode: Celery tasks live in `webapp/tasks.py` and `webapp/celery_app.py` (broker/backend via `REDIS_URL`), plus Docker Compose for local testing (`docker-compose.yml`).
- Packaging: macOS packaging is driven by scripts in `scripts/` (`package_mac.sh`, `verify_macos_artifact.py`). Swift prototype in `swift/` is separate (use `swift test` / `swift build`).

How to run locally (key commands) ✅
- Dev env: `python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`
- GUI: `python run_gui.py` (or `python -m run_gui`)
- Web API: `uvicorn webapp.main:app --reload --host 127.0.0.1 --port 8000`
- Celery (optional): `pip install -r webapp/requirements.txt` then `celery -A webapp.tasks worker --loglevel=info` (requires `REDIS_URL`)
- Docker Compose: `docker-compose up --build` starts `web`, `redis`, and `celery` services
- Package macOS: `bash scripts/package_mac.sh` then `python3 scripts/verify_macos_artifact.py dist`

Testing & CI 🔧
- Unit + GUI tests: `pytest` (GUI tests run headless in CI using `xvfb` and `QT_QPA_PLATFORM=offscreen`).
- Run headless locally: `QT_QPA_PLATFORM=offscreen pytest` (or use `xvfb-run` on Linux).
- Integration (Redis + Celery): CI uses a Redis service and starts a Celery worker; run locally via Makefile target `make test-ci` or set `RUN_CELERY_INTEGRATION=1 REDIS_URL=redis://localhost:6379/0 USE_CELERY=1` and start a worker.
- Important CI notes: viewer E2E tests are selectively run in `viewer-e2e` job and require `xvfb`.

Project-specific patterns & conventions 🧭
- Callbacks: Integrate with the crawler using two callbacks: `progress_callback(completed: int, total: int)` and `metrics_callback(url, response_time, status_code)`; GUI `Worker` and `webapp` local runner rely on these.
- Persistent tasks: `webapp/store.py` keeps `tasks.json` and per-task `events.log` lines (JSON per line). When modifying task persistence, update the restore logic in `webapp/main.py` (AUTO_RESUME behavior).
- Env-driven features: respect `AUTO_RESUME` (default `1`), `USE_CELERY`, `REDIS_URL`, `WEBAPP_API_KEY` (simple auth), `RATE_LIMIT_MAX`, `RATE_LIMIT_WINDOW`. CI also sets `QT_QPA_PLATFORM=offscreen`.
- Files / outputs:
  - reports: `<output_dir>/seo_report.json`, `<output_dir>/seo_data.csv`
  - DB: `<output_dir>/crawl_data.db`
  - tasks: `webapp/data/tasks.json`, events `webapp/data/<id>/events.log`
- Threading & signals: GUI Worker runs crawler in a dedicated thread; prefer emitting signals or using callbacks rather than blocking main thread.

Integration points & external dependencies 🔌
- Redis (pub/sub and rate limiter), Celery (task queue), PySide6 (desktop GUI), FastAPI + Uvicorn (web API), PyInstaller (packaging), Swift toolchain for `swift/` demo.
- Docker image publishing: `.github/workflows/publish-image.yml` pushes images to GHCR on tags/releases.

Quick examples (copy/paste) 💡
- Start a local crawl (curl):
  curl -v -X POST "http://127.0.0.1:8000/start" -H "Content-Type: application/json" -H "X-API-KEY: <key>" -d '{"base_url":"https://example.com","max_pages":1}'
- SSE poll: `curl http://127.0.0.1:8000/events/<task_id>`
- WebSocket JSON messages: connect to `ws://127.0.0.1:8000/ws/<task_id>`

Notes for AI agents (how to contribute) 🤖
- Prefer small, focused PRs with tests. When changing APIs (task persistence, event format, stored keys), update `webapp/main.py` resume logic and `webapp/tasks.py` and add migration steps in tests.
- When touching GUI behavior, run GUI tests headless (`QT_QPA_PLATFORM=offscreen`) and avoid UI thread blocking; use `Worker` patterns and signals.
- For Celery/Redis changes, mirror behavior in `webapp/tasks.py` (publish events to Redis using `task_events:<id>`) and update the pubsub listener in `webapp/main.py`.

Where to look first (fast paths) 🔭
- Start here: `README.md`, `webapp/README.md`, `.github/workflows/ci.yml`
- Core behavior: `Crawler.py` (crawler internals), `gui/worker.py` (how the crawler is used), `webapp/main.py` (API & persistence), `webapp/tasks.py` (Celery integration)

If anything here is unclear or you want more examples (API payloads, test patterns, or packaging subtleties), tell me which area to expand and I will iterate. 🙌
