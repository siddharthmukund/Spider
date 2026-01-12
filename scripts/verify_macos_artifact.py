#!/usr/bin/env python3
"""Verify a macOS .app artifact.

Usage: python scripts/verify_macos_artifact.py <artifacts_dir>

Checks:
- Finds first .app in the directory
- Validates Info.plist exists
- Optionally runs the app headlessly for a short smoke run (QT_QPA_PLATFORM=offscreen)

Exit code: 0 on success, non-zero on failure.
"""

import sys
import subprocess
import time
from pathlib import Path


def fail(msg: str):
    print("ERROR:", msg)
    sys.exit(2)


def main():
    if len(sys.argv) < 2:
        fail("Usage: verify_macos_artifact.py <artifacts_dir>")

    artifacts = Path(sys.argv[1])
    if not artifacts.exists():
        fail(f"Artifacts directory does not exist: {artifacts}")

    apps = list(artifacts.glob('**/*.app'))
    if not apps:
        fail("No .app bundle found in artifacts")

    app = apps[0]
    print("Found app:", app)

    info = app / 'Contents' / 'Info.plist'
    if not info.exists():
        fail(f"Info.plist missing in {app}")

    print("Info.plist present")

    # Locate executable inside Contents/MacOS
    macos_dir = app / 'Contents' / 'MacOS'
    if not macos_dir.exists():
        fail("Contents/MacOS missing in app bundle")

    exe_candidates = [p for p in macos_dir.iterdir() if p.is_file() and p.stat().st_mode & 0o111]
    # Fallback: any file
    if not exe_candidates:
        exe_candidates = [p for p in macos_dir.iterdir() if p.is_file()]

    if not exe_candidates:
        fail("No executable found in Contents/MacOS")

    exe = exe_candidates[0]
    print("Executable:", exe)

    # Run codesign -d --verbose=4 to provide additional info (non-fatal)
    try:
        out = subprocess.check_output(['codesign', '-d', '--verbose=4', str(app)], stderr=subprocess.STDOUT)
        print('codesign info:')
        print(out.decode('utf8', errors='replace'))
    except FileNotFoundError:
        print('codesign not available on PATH, skipping codesign check')
    except subprocess.CalledProcessError as e:
        print('codesign returned non-zero (continuing):')
        print(e.output.decode('utf8', errors='replace'))

    # Run a short offscreen smoke-launch
    env = dict(**dict(subprocess.os.environ))
    env['QT_QPA_PLATFORM'] = 'offscreen'

    print('Launching app for a short headless smoke test (3s)')
    proc = subprocess.Popen([str(exe)], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        # Wait 1s and ensure process is still running
        time.sleep(1)
        if proc.poll() is not None:
            out, err = proc.communicate(timeout=1)
            fail(f'App exited immediately. stdout={out[:200]!r} stderr={err[:200]!r}')
        # Let it run a bit longer (total ~3s), then terminate
        time.sleep(2)
        proc.terminate()
        proc.wait(timeout=5)
        print('App smoke run succeeded (terminated after short run)')
    except Exception as e:
        try:
            proc.kill()
        except Exception:
            pass
        fail(f'App smoke test failed: {e}')

    # Optionally inspect stderr for fatal messages
    try:
        out, err = proc.communicate(timeout=1)
    except Exception:
        out, err = b'', b''

    stderr = err.decode('utf8', errors='replace').lower()
    if 'error' in stderr and 'qt' in stderr:
        print('Warning: Qt-related errors in stderr:')
        print(err.decode('utf8', errors='replace'))

    print('Verification complete')
    return 0


if __name__ == '__main__':
    sys.exit(main())
