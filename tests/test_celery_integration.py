import os
import time
import uuid
import pytest

from webapp import store

pytestmark = pytest.mark.skipif(os.getenv('RUN_CELERY_INTEGRATION') != '1', reason='integration tests disabled')

from webapp.tasks import run_crawl_task


def test_celery_run_creates_report(tmp_path):
    # Arrange
    task_id = str(uuid.uuid4())
    out = tmp_path / task_id
    out.mkdir()
    # create initial task entry so Celery task can update it
    tasks = store.load_tasks()
    tasks[task_id] = {
        'id': task_id,
        'status': 'queued',
        'report': None,
        'base_url': 'https://example.com',
        'max_pages': 1,
        'max_workers': 1,
        'output_dir': str(out)
    }
    store.save_tasks(tasks)

    # Act: enqueue and run the task via Celery (worker must be running in CI)
    run_crawl_task.delay('https://example.com', 1, 1, str(out), task_id)

    # Wait up to 30s for the worker to process and update tasks.json
    for _ in range(30):
        tasks = store.load_tasks()
        t = tasks.get(task_id, {})
        if t.get('status') == 'finished':
            break
        time.sleep(1)

    tasks = store.load_tasks()
    t = tasks.get(task_id, {})
    assert t.get('status') == 'finished', f"Task did not finish, status={t.get('status')}"
    report = out / 'seo_report.json'
    assert report.exists(), 'Report file not created'
