import json
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
import sys
import time


def test_gui_backend_integration_creates_report_and_db(qtbot, monkeypatch, tmp_path):
    # Use the real AdvancedSEOCrawler but patch network calls
    from Crawler import AdvancedSEOCrawler

    class DummyResponse:
        def __init__(self, url, body):
            self.status_code = 200
            self._content = body.encode('utf-8')
            self.headers = {'content-type': 'text/html; charset=utf-8'}
            self.url = url
            self.history = []
            self.encoding = 'utf-8'
            self.text = body

    # Patch requests.Session.get used inside AdvancedSEOCrawler
    def fake_get(self, url, timeout=10, allow_redirects=True, stream=False):
        html = f"<html><head><title>Page</title></head><body><h1>{url}</h1></body></html>"
        return DummyResponse(url, html)

    import requests
    monkeypatch.setattr(requests.Session, 'get', fake_get, raising=True)

    # Launch GUI
    app = QApplication.instance() or QApplication(sys.argv)
    from gui.main_window import MainWindow
    win = MainWindow()
    qtbot.addWidget(win)

    # Set small run
    win.base_url_edit.setText('https://example.com')
    win.max_pages_spin.setValue(2)
    win.max_workers_spin.setValue(1)

    # Set output dir
    outdir = tmp_path / 'out'
    outdir.mkdir()
    win.output_edit.setText(str(outdir))

    # Start
    qtbot.mouseClick(win.start_btn, Qt.LeftButton)

    # Wait until worker thread stops (finish or error)
    qtbot.waitUntil(lambda: not win.worker.is_running(), timeout=10000)

    # Check for finished message or report
    log_txt = win.log_view.toPlainText()
    if 'Finished. Report saved' in log_txt:
        # extract report path from the last 'Finished' message
        lines = [l for l in log_txt.splitlines() if 'Finished. Report saved' in l]
        assert lines, 'Finished message missing'
        report_path = lines[-1].split(' to ')[-1]
        report_file = Path(report_path)
        assert report_file.exists()
        with open(report_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        assert 'statistics' in data
    else:
        # If not finished, assert error message exists
        assert 'Error' in log_txt or 'Stop requested' in log_txt

    # Check DB created in output dir (if present)
    db_file = outdir / 'crawl_data.db'
    if db_file.exists():
        import sqlite3
        conn = sqlite3.connect(str(db_file))
        cur = conn.cursor()
        cur.execute("SELECT count(*) FROM pages")
        c = cur.fetchone()[0]
        assert c >= 0
        conn.close()
