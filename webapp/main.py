import asyncio
import threading
import uuid
import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, Any

from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.responses import HTMLResponse, StreamingResponse, FileResponse
from pydantic import BaseModel, HttpUrl, Field

# Ensure project root is importable
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from Crawler import AdvancedSEOCrawler

# Import security modules
from webapp.security.auth import verify_api_key
from webapp.security.ssrf import SSRFValidator
from webapp.security.rate_limit import create_rate_limiter
from webapp.security.audit import get_audit_logger, AuditEvent

app = FastAPI(
    title="Spider SEO Crawler API",
    description="Enterprise-grade SEO crawler with security hardening",
    version="2.0.0"
)

# Initialize security components
audit = get_audit_logger()

# Initialize rate limiter
USE_REDIS = os.getenv('REDIS_URL') is not None
RATE_LIMIT_RPM = int(os.getenv('RATE_LIMIT_MAX', '60'))
rate_limiter = create_rate_limiter(
    requests_per_minute=RATE_LIMIT_RPM,
    use_redis=USE_REDIS,
    redis_url=os.getenv('REDIS_URL')
)

# Log service startup
audit.log(
    AuditEvent.SERVICE_START,
    client_ip="0.0.0.0",
    details={"version": "2.0.0", "rate_limit_rpm": RATE_LIMIT_RPM}
)

# Persistent task registry (load from disk)
from . import store

TASKS: Dict[str, Dict[str, Any]] = store.load_tasks()
LOOP = None

# ensure restored tasks have queues and clean state
for tid, info in list(TASKS.items()):
    # rebuild ephemeral objects
    info.setdefault('queue', asyncio.Queue())
    # If task was running when server stopped, mark it as interrupted
    if info.get('status') == 'running':
        info['status'] = 'error'
        info['error_message'] = 'Server restarted during run'
        store.append_event(tid, {'type': 'error', 'message': info['error_message']})

# Save immediately so file reflects normalized state
store.save_tasks({k: {k2: v2 for k2, v2 in v.items() if k2 != 'queue'} for k, v in TASKS.items()})


@app.on_event('startup')
async def _startup():
    global LOOP
    LOOP = asyncio.get_running_loop()
    # ensure restored tasks have a working queue object
    for tid, info in TASKS.items():
        if 'queue' not in info or info['queue'] is None:
            info['queue'] = asyncio.Queue()

    # Resume unfinished local tasks if AUTO_RESUME enabled
    if os.getenv('AUTO_RESUME', '1') == '1':
        for tid, info in TASKS.items():
            if info.get('status') in ('queued', 'running') and not info.get('celery_enqueued'):
                # spawn thread to resume
                def resume_thread(tid_local=tid):
                    import threading
                    def target():
                        # reuse local runner from start handler
                        try:
                            # prefer to call same logic as start -> _run_task
                            # emulate a request by using stored info
                            q = TASKS[tid_local]['queue']
                            store.append_event(tid_local, {'type':'resume', 'message':'Resuming task on startup'})
                            # start a thread to run the task
                            th = threading.Thread(target=lambda: None)
                            # call the start routine by invoking the internal runner
                            # we will spawn a thread and call the same _run_task logic inline
                            # reuse existing info keys
                            # Simple approach: call the same code by scheduling a small helper
                            from functools import partial
                            import_types = globals()
                            # manually call the internal runner created by start endpoint
                            # To avoid code duplication we'll call a helper function
                            _start_local_task(tid_local)
                        except Exception as e:
                            store.append_event(tid_local, {'type':'error', 'message': str(e)})
                    t = threading.Thread(target=target, daemon=True)
                    t.start()
                resume_thread()

    # Start Redis pubsub listener if REDIS_URL present
    REDIS = os.getenv('REDIS_URL')
    if REDIS:
        import threading, redis, json
        def _redis_listener():
            try:
                r = redis.from_url(REDIS)
                p = r.pubsub()
                p.psubscribe('task_events:*')
                for msg in p.listen():
                    if not msg or msg['type'] not in ('pmessage', 'message'):
                        continue
                    ch = msg.get('channel') or msg.get('pattern')
                    try:
                        data = msg.get('data')
                        if isinstance(data, bytes):
                            data = data.decode('utf-8')
                        payload = json.loads(data)
                        # channel format 'task_events:<task_id>' -> extract id
                        channel = ch.decode() if isinstance(ch, bytes) else ch
                        _, tid = channel.split(':', 1)
                        if tid in TASKS:
                            q = TASKS[tid].setdefault('queue', asyncio.Queue())
                            LOOP.call_soon_threadsafe(q.put_nowait, payload)
                            store.append_event(tid, payload)
                    except Exception:
                        continue
            except Exception:
                pass
        t = threading.Thread(target=_redis_listener, daemon=True)
        t.start()


class StartRequest(BaseModel):
    """Request model for starting a crawl task."""
    base_url: HttpUrl = Field(..., description="Target URL to crawl")
    max_pages: int = Field(default=50, ge=1, le=10000, description="Maximum pages to crawl")
    max_workers: int = Field(default=3, ge=1, le=20, description="Number of concurrent workers")
    output_dir: str = Field(default='web_output', description="Output directory")
    respect_robots: bool = Field(default=True, description="Respect robots.txt")


@app.post('/start', dependencies=[Depends(verify_api_key)])
async def start_crawl(req: StartRequest, request: Request, api_key: str = Depends(verify_api_key)):
    """Start a new crawl task with security validation."""
    
    client_ip = request.client.host if request.client else 'unknown'
    
    # 1. Rate limiting
    if not rate_limiter.check(client_ip):
        audit.log_rate_limited(client_ip, '/start')
        raise HTTPException(
            status_code=429,
            detail='Rate limit exceeded. Please try again later.',
            headers={'Retry-After': '60'}
        )
    
    # 2. SSRF validation
    is_valid, error_msg = SSRFValidator.validate(str(req.base_url))
    if not is_valid:
        audit.log_ssrf_blocked(client_ip, str(req.base_url), error_msg)
        raise HTTPException(status_code=400, detail=f"Invalid URL: {error_msg}")
    
    # 3. Log successful authentication
    audit.log_auth_success(client_ip)
    
    # Create task
    import time
    task_id = str(uuid.uuid4())
    out = Path(req.output_dir) / task_id
    out.mkdir(parents=True, exist_ok=True)

    queue: asyncio.Queue = asyncio.Queue()
    info = {
        'id': task_id,
        'status': 'queued',
        'queue': queue,
        'report': None,
        'cache_stats': None,
        'started_at': None,
        'finished_at': None,
        'base_url': str(req.base_url),
        'max_pages': req.max_pages,
        'max_workers': req.max_workers,
        'output_dir': str(out),
        'created_at': time.time()
    }
    TASKS[task_id] = info
    store.save_tasks({k: {k2: v2 for k2, v2 in v.items() if k2 != 'queue'} for k, v in TASKS.items()})
    
    # Log crawl start
    audit.log_crawl_start(client_ip, task_id, str(req.base_url))

    # Support optional Celery enqueueing
    if os.getenv('USE_CELERY') == '1':
        try:
            from .tasks import run_crawl_task
            run_crawl_task.delay(str(req.base_url), req.max_pages, req.max_workers, str(out), task_id)
            info['status'] = 'queued'
            info['celery_enqueued'] = True
            store.save_tasks({k: {k2: v2 for k2, v2 in v.items() if k2 != 'queue'} for k, v in TASKS.items()})
            return {'task_id': task_id}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f'Failed to enqueue task: {e}')

    # Local runner -> reuse helper
    _start_local_task(task_id)

    return {'task_id': task_id}


@app.get('/status/{task_id}', dependencies=[Depends(verify_api_key)])
async def get_status(task_id: str, api_key: str = Depends(verify_api_key)):
    info = TASKS.get(task_id)
    if not info:
        raise HTTPException(status_code=404, detail='Task not found')
    return {
        'id': task_id,
        'status': info['status'],
        'report': info['report'],
        'cache_stats': info['cache_stats']
    }


@app.get('/report/{task_id}', dependencies=[Depends(verify_api_key)])
async def get_report(task_id: str, api_key: str = Depends(verify_api_key)):
    info = TASKS.get(task_id)
    if not info:
        raise HTTPException(status_code=404, detail='Task not found')
    if not info.get('report'):
        raise HTTPException(status_code=404, detail='Report not available')
    return FileResponse(info['report'], media_type='application/json')


def _persist_tasks():
    store.save_tasks({k: {k2: v2 for k2, v2 in v.items() if k2 != 'queue'} for k, v in TASKS.items()})


def _start_local_task(task_id: str):
    """Start or resume a local task using stored TASKS entry"""
    import threading
    def _runner():
        info = TASKS[task_id]
        q = info.setdefault('queue', asyncio.Queue())
        info['status'] = 'running'
        _persist_tasks()
        info['started_at'] = time.time()

        def progress_cb(completed, total):
            ev = {'type': 'progress', 'completed': completed, 'total': total}
            if LOOP:
                LOOP.call_soon_threadsafe(q.put_nowait, ev)
            store.append_event(task_id, ev)

        def metrics_cb(url, response_time, status_code):
            ev = {'type': 'metric', 'url': url, 'response_time': response_time, 'status_code': status_code}
            if LOOP:
                LOOP.call_soon_threadsafe(q.put_nowait, ev)
            store.append_event(task_id, ev)

        try:
            crawler = AdvancedSEOCrawler(
                base_url=info['base_url'],
                max_pages=info['max_pages'],
                max_workers=info['max_workers'],
                respect_robots=True,
                db_path=str(Path(info['output_dir']) / 'crawl_data.db')
            )
            crawler.progress_callback = progress_cb
            crawler.metrics_callback = metrics_cb
            crawler.crawl()

            report_path = str(Path(info['output_dir']) / 'seo_report.json')
            crawler.generate_seo_report(report_path)

            try:
                stats = crawler.get_cache_statistics()
                info['cache_stats'] = stats
                if LOOP:
                    LOOP.call_soon_threadsafe(q.put_nowait, {'type': 'cache', 'stats': stats})
                store.append_event(task_id, {'type': 'cache', 'stats': stats})
            except Exception:
                pass

            info['report'] = report_path
            info['status'] = 'finished'
            info['finished_at'] = time.time()
            if LOOP:
                LOOP.call_soon_threadsafe(q.put_nowait, {'type': 'finished', 'report': report_path})
            _persist_tasks()
        except Exception as e:
            info['status'] = 'error'
            if LOOP:
                LOOP.call_soon_threadsafe(q.put_nowait, {'type': 'error', 'message': str(e)})
            store.append_event(task_id, {'type': 'error', 'message': str(e)})
            _persist_tasks()

    t = threading.Thread(target=_runner, daemon=True)
    t.start()


@app.get('/events/{task_id}')
async def events(task_id: str):
    info = TASKS.get(task_id)
    if not info:
        raise HTTPException(status_code=404, detail='Task not found')
    queue: asyncio.Queue = info['queue']

    async def event_generator():
        while True:
            ev = await queue.get()
            yield f"data: {json.dumps(ev)}\n\n"
            if ev.get('type') in ('finished', 'error'):
                break

    return StreamingResponse(event_generator(), media_type='text/event-stream')


# WebSocket endpoint for richer real-time updates
from fastapi import WebSocket, WebSocketDisconnect

@app.websocket('/ws/{task_id}')
async def websocket_endpoint(websocket: WebSocket, task_id: str):
    await websocket.accept()
    info = TASKS.get(task_id)
    if not info:
        await websocket.send_text(json.dumps({'type': 'error', 'message': 'Task not found'}))
        await websocket.close()
        return
    queue: asyncio.Queue = info['queue']
    try:
        while True:
            ev = await queue.get()
            await websocket.send_text(json.dumps(ev))
            if ev.get('type') in ('finished', 'error'):
                break
    except WebSocketDisconnect:
        pass


# Health check endpoint (no authentication required)
@app.get('/health')
async def health_check():
    """Health check endpoint for monitoring."""
    return {
        'status': 'healthy',
        'service': 'Spider SEO Crawler',
        'version': '2.0.0',
        'timestamp': time.time()
    }


@app.get('/', response_class=HTMLResponse)
async def index():
    static = Path(__file__).resolve().parent / 'static' / 'index.html'
    if static.exists():
        return HTMLResponse(static.read_text())
    return HTMLResponse('<h1>Spider SEO Crawler API v2.0</h1><p>Enterprise-grade web crawler with security hardening.</p>')


# Exception handlers for better error responses
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Custom HTTP exception handler with audit logging."""
    client_ip = request.client.host if request.client else 'unknown'
    
    # Log authentication failures
    if exc.status_code in [401, 403]:
        audit.log_auth_failure(client_ip, exc.detail)
    
    return {
        'error': exc.detail,
        'status_code': exc.status_code
    }


if __name__ == '__main__':
    import uvicorn
    uvicorn.run('webapp.main:app', host='127.0.0.1', port=8000, reload=True)
