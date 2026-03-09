from .celery_app import make_celery
from pathlib import Path
import json

celery = make_celery()

@celery.task(name='webapp.tasks.run_crawl_task')
def run_crawl_task(base_url, max_pages, max_workers, out_dir, task_id):
    # Minimal celery task that runs a crawl and writes report to out_dir
    from Crawler import AdvancedSEOCrawler
    from . import store
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    def progress_cb(completed, total):
        store.append_event(task_id, {'type': 'progress', 'completed': completed, 'total': total})

    def metrics_cb(url, response_time, status_code):
        store.append_event(task_id, {'type': 'metric', 'url': url, 'response_time': response_time, 'status_code': status_code})

    try:
        crawler = AdvancedSEOCrawler(base_url=base_url, max_pages=max_pages, max_workers=max_workers, db_path=str(out / 'crawl_data.db'))
        crawler.progress_callback = progress_cb
        crawler.metrics_callback = metrics_cb
        crawler.crawl()
        report = str(out / 'seo_report.json')
        crawler.generate_seo_report(report)
        try:
            stats = crawler.get_cache_statistics()
            store.append_event(task_id, {'type': 'cache', 'stats': stats})
            # publish to Redis channel for live forwarding
            import os, json, redis
            REDIS = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
            try:
                r = redis.from_url(REDIS)
                r.publish(f'task_events:{task_id}', json.dumps({'type':'cache', 'stats': stats}))
            except Exception:
                pass
        except Exception:
            pass
        # store minimal task state
        data = store.load_tasks()
        t = data.get(task_id, {})
        t['status'] = 'finished'
        t['report'] = report
        store.save_tasks(data)
    except Exception as e:
        store.append_event(task_id, {'type': 'error', 'message': str(e)})
        # publish errors too
        try:
            import os, json, redis
            REDIS = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
            r = redis.from_url(REDIS)
            r.publish(f'task_events:{task_id}', json.dumps({'type':'error', 'message': str(e)}))
        except Exception:
            pass
        data = store.load_tasks()
        t = data.get(task_id, {})
        t['status'] = 'error'
        store.save_tasks(data)
