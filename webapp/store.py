import json
from pathlib import Path
from typing import Dict, Any

# allow tests or deployments to redirect the storage directory
# by setting WEBAPP_DATA_DIR environment variable
_data_base = os.getenv('WEBAPP_DATA_DIR')
if _data_base:
    DATA_DIR = Path(_data_base)
else:
    DATA_DIR = Path(__file__).resolve().parent / 'data'
TASKS_FILE = DATA_DIR / 'tasks.json'

DATA_DIR.mkdir(exist_ok=True, parents=True)


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


# --- User management (Phase 3) ------------------------------------------------
USERS_FILE = DATA_DIR / 'users.json'


def load_users() -> dict:
    """Return the user database (username -> record)."""
    if USERS_FILE.exists():
        try:
            with open(USERS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_users(users: dict):
    """Persist the user database to disk."""
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(users, f, indent=2)


def add_user(username: str, hashed_password: str, **kwargs) -> dict:
    """Create or update a user record."""
    users = load_users()
    record = {
        'username': username,
        'hashed_password': hashed_password,
        'scopes': kwargs.get('scopes', []),
        'is_active': kwargs.get('is_active', True),
        'is_superuser': kwargs.get('is_superuser', False),
        'api_keys': kwargs.get('api_keys', [])
    }
    users[username] = record
    save_users(users)
    return record


def get_user(username: str) -> dict | None:
    """Lookup user record by username."""
    users = load_users()
    return users.get(username)


def set_api_key(username: str, api_key_hash: str):
    """Append a hashed API key to a user."""
    users = load_users()
    user = users.get(username)
    if not user:
        raise KeyError("user not found")
    user.setdefault('api_keys', []).append(api_key_hash)
    save_users(users)


def list_users() -> list:
    """Return list of all usernames."""
    return list(load_users().keys())


def verify_user_password(username: str, hashed: str) -> bool:
    """Check whether hashed password matches user's stored hash."""
    user = get_user(username)
    if not user:
        return False
    return hashed == user.get('hashed_password')
