import subprocess
import sys
from pathlib import Path
import plistlib


def package_app(entry_point: str = 'run_gui.py', name: str = 'SEO Crawler', icon: str | None = None, bundle_id: str | None = None, version: str | None = None) -> Path:
    """Runs pyinstaller to create macOS app; returns path to dist directory.

    Optional arguments:
      - icon: path to .icns file
      - bundle_id: CFBundleIdentifier to set
      - version: CFBundleShortVersionString to set
    """
    cmd = [
        sys.executable, '-m', 'PyInstaller', '--noconfirm', '--name', name, '--windowed', entry_point
    ]
    if icon:
        cmd += ['--icon', str(icon)]
    if bundle_id:
        cmd += ['--osx-bundle-identifier', bundle_id]

    print('Running:', ' '.join(cmd))
    subprocess.run(cmd, check=True)

    # Post-build: update Info.plist for version if provided
    app_path = Path('dist') / f"{name}.app"
    info_plist = app_path / 'Contents' / 'Info.plist'
    if version and info_plist.exists():
        try:
            print('Updating Info.plist with version', version)
            data = plistlib.loads(info_plist.read_bytes())
            data['CFBundleShortVersionString'] = version
            info_plist.write_bytes(plistlib.dumps(data))
        except Exception as e:
            print('Failed to update Info.plist:', e)

    return Path('dist')


if __name__ == '__main__':
    # Read args from env or fallback defaults
    entry = sys.argv[1] if len(sys.argv) > 1 else 'run_gui.py'
    name = sys.argv[2] if len(sys.argv) > 2 else 'SEO Crawler'
    icon = sys.argv[3] if len(sys.argv) > 3 and sys.argv[3] != 'None' else None
    bundle_id = sys.argv[4] if len(sys.argv) > 4 and sys.argv[4] != 'None' else None
    version = sys.argv[5] if len(sys.argv) > 5 and sys.argv[5] != 'None' else None

    dist = package_app(entry_point=entry, name=name, icon=icon, bundle_id=bundle_id, version=version)
    print('Packaged to', dist)
