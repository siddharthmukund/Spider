import os
import subprocess
from pathlib import Path


def test_package_app_smoke(monkeypatch, tmp_path):
    created = {'called': False}

    def fake_run(cmd, check=True):
        # Simulate creating dist output
        created['called'] = True
        d = tmp_path / 'dist'
        d.mkdir()
        (d / 'SEO Crawler.app').mkdir()
        return 0

    import scripts.package_mac as pm
    monkeypatch.setattr(pm.subprocess, 'run', fake_run)

    # Change cwd to tmp_path to avoid polluting repo
    cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        dist = pm.package_app()
        assert created['called']
        assert (tmp_path / 'dist' / 'SEO Crawler.app').exists()
    finally:
        os.chdir(cwd)
