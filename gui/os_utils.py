import sys
import subprocess
from pathlib import Path
import shutil


def open_path(path: str) -> bool:
    """Open a file or directory with the default OS handler.
    Returns True on success, False otherwise.
    """
    p = Path(path)
    if not p.exists():
        return False

    try:
        if sys.platform == 'darwin':
            subprocess.run(['open', str(p)])
        elif sys.platform.startswith('linux'):
            if shutil.which('xdg-open'):
                subprocess.run(['xdg-open', str(p)])
            else:
                # Fallback to running without opening
                return False
        elif sys.platform.startswith('win'):
            subprocess.run(['start', str(p)], shell=True)
        else:
            return False
        return True
    except Exception:
        return False
