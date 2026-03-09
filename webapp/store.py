import json
from pathlib import Path
from typing import Dict, Any

DATA_DIR = Path(__file__).resolve().parent / 'data'
TASKS_FILE = DATA_DIR / 'tasks.json'

DATA_DIR.mkdir(exist_ok=True)


def load_tasks() -> Dict[str, Dict[str, Any]]:
    if TASKS_FILE.exists():
        try:
            with open(TASKS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_tasks(tasks: Dict[str, Dict[str, Any]]):
    with open(TASKS_FILE, 'w', encoding='utf-8') as f:
        json.dump(tasks, f, indent=2)


def append_event(task_id: str, ev: Dict[str, Any]):
    task_dir = DATA_DIR / task_id
    task_dir.mkdir(exist_ok=True)
    events_file = task_dir / 'events.log'
    with open(events_file, 'a', encoding='utf-8') as f:
        f.write(json.dumps(ev) + '\n')


def read_events(task_id: str):
    task_dir = DATA_DIR / task_id
    events_file = task_dir / 'events.log'
    if not events_file.exists():
        return []
    with open(events_file, 'r', encoding='utf-8') as f:
        return [json.loads(l) for l in f if l.strip()]
