import time
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
import sys


def test_progress_and_finish(qtbot, monkeypatch, tmp_path):
    # Dummy crawler that reports progress and creates a fake report file
    class DummyCrawler:
        def __init__(self, base_url, max_pages, max_workers):
            self.base_url = base_url
            self.max_pages = max_pages
            self.max_workers = max_workers
            self.progress_callback = None
            self.metrics_callback = None
            self.interrupted = False

        def crawl(self):
            for i in range(self.max_pages):
                if self.interrupted:
                    break
                time.sleep(0.01)
                if self.metrics_callback:
                    self.metrics_callback(f'{self.base_url}/page{i+1}', 0.01 * (i+1), 200)
                if self.progress_callback:
                    self.progress_callback(i + 1, self.max_pages)

        def generate_seo_report(self, path):
            with open(path, 'w', encoding='utf-8') as f:
                f.write('{}')

    # Patch the crawler used by the worker
    import gui.worker as gw
    monkeypatch.setattr(gw, 'AdvancedSEOCrawler', DummyCrawler)

    app = QApplication.instance() or QApplication(sys.argv)
    from gui.main_window import MainWindow
    win = MainWindow()
    qtbot.addWidget(win)

    # Use a tmp output dir
    win.output_edit.setText(str(tmp_path))

    # Start the crawl (max_pages small to keep test fast)
    win.max_pages_spin.setValue(3)
    qtbot.mouseClick(win.start_btn, Qt.LeftButton)

    # Wait for finished signal
    with qtbot.waitSignal(win.worker.finished, timeout=2000) as blocker:
        pass

    # Check progress reached 100%
    assert win.progress.value() == 100
    assert 'Finished' in win.log_view.toPlainText() or 'report' in win.log_view.toPlainText()


def test_stop_requests_stop(qtbot, monkeypatch):
    class SlowCrawler:
        def __init__(self, base_url, max_pages, max_workers):
            self.base_url = base_url
            self.max_pages = max_pages
            self.max_workers = max_workers
            self.progress_callback = None
            self.metrics_callback = None
            self.interrupted = False

        def crawl(self):
            for i in range(100):
                if self.interrupted:
                    break
                time.sleep(0.02)
                if self.metrics_callback:
                    self.metrics_callback(f'{self.base_url}/page{i+1}', 0.02 * (i+1), 200)
                if self.progress_callback:
                    self.progress_callback(i + 1, 100)

        def generate_seo_report(self, path):
            with open(path, 'w', encoding='utf-8') as f:
                f.write('{}')

    import gui.worker as gw
    monkeypatch.setattr(gw, 'AdvancedSEOCrawler', SlowCrawler)

    from gui.main_window import MainWindow
    app = QApplication.instance() or QApplication(sys.argv)
    win = MainWindow()
    qtbot.addWidget(win)

    win.max_pages_spin.setValue(100)

    qtbot.mouseClick(win.start_btn, Qt.LeftButton)

    # Wait until some progress is made
    qtbot.waitUntil(lambda: win.progress.value() > 0, timeout=1000)

    # Click stop
    qtbot.mouseClick(win.stop_btn, Qt.LeftButton)

    # Wait until worker stops
    qtbot.waitUntil(lambda: not win.worker.is_running(), timeout=2000)

    # Confirm that stop-related log exists and UI buttons reset
    txt = win.log_view.toPlainText()
    assert 'Stop requested' in txt
    assert win.start_btn.isEnabled()
    assert not win.stop_btn.isEnabled()
