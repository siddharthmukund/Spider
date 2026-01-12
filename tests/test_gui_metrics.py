from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
import sys
import time


def test_metrics_table_and_sparkline(qtbot, monkeypatch):
    # Dummy crawler that emits metrics
    class DummyCrawler:
        def __init__(self, base_url, max_pages, max_workers):
            self.base_url = base_url
            self.max_pages = max_pages
            self.max_workers = max_workers
            self.metrics_callback = None
            self.progress_callback = None
            self.interrupted = False

        def crawl(self):
            for i in range(5):
                if self.interrupted:
                    break
                time.sleep(0.01)
                if self.metrics_callback:
                    self.metrics_callback(f'{self.base_url}/p{i+1}', 0.01*(i+1), 200)
                if self.progress_callback:
                    self.progress_callback(i+1, self.max_pages)

        def generate_seo_report(self, path):
            with open(path, 'w') as f:
                f.write('{}')

    import gui.worker as gw
    monkeypatch.setattr(gw, 'AdvancedSEOCrawler', DummyCrawler)

    app = QApplication.instance() or QApplication(sys.argv)
    from gui.main_window import MainWindow
    win = MainWindow()
    qtbot.addWidget(win)

    win.max_pages_spin.setValue(5)
    qtbot.mouseClick(win.start_btn, Qt.LeftButton)

    # Wait for finished
    qtbot.waitSignal(win.worker.finished, timeout=2000)

    # Wait until table is populated (sometimes async)
    qtbot.waitUntil(lambda: win.metrics_table.rowCount() >= 5, timeout=2000)

    # Check table rows
    assert win.metrics_table.rowCount() >= 5
    # Check labels updated
    assert 'Avg' in win.avg_label.text()
    assert 'Fastest' in win.fastest_label.text()
    assert 'Slowest' in win.slowest_label.text()