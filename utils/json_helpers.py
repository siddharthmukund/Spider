from datetime import datetime
from dataclasses import is_dataclass, asdict
from collections import defaultdict
from enum import Enum
import json
from typing import Any


def to_serializable(obj: Any):
    """Convert common non-JSON types to serializable representations."""
    # dataclasses -> dict
    if is_dataclass(obj):
        return asdict(obj)
    # datetime -> ISO string
    if isinstance(obj, datetime):
        return obj.isoformat()
    # defaultdict -> dict
    if isinstance(obj, defaultdict):
        return dict(obj)
    # enum -> value
    if isinstance(obj, Enum):
        return obj.value
    # sets -> list
    if isinstance(obj, set):
        return list(obj)
    # bytes -> decode
    if isinstance(obj, (bytes, bytearray)):
        try:
            return obj.decode('utf-8')
        except Exception:
            return str(obj)
    # fallback
    raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")


class JsonEncoder(json.JSONEncoder):
    """JSON Encoder using to_serializable fallback."""
    def default(self, obj: Any):
        try:
            return to_serializable(obj)
        except TypeError:
            return super().default(obj)
