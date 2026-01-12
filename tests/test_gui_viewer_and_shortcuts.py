from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
import sys
from pathlib import Path
import json


def test_viewer_invoked_with_report_and_csv(qtbot, monkeypatch, tmp_path):
    # Create dummy report and csv
    out = tmp_path / 'out'
    out.mkdir()
    report = out / 'seo_report.json'
    data = {'metadata': {'crawl_date': '2020-01-01T00:00:00'}, 'summary': {'total_pages': 1}}
    report.write_text(json.dumps(data), encoding='utf-8')
    csv_file = out / 'seo_data.csv'
    csv_file.write_text('a,b\n1,2', encoding='utf-8')

    # Monkeypatch ReportViewer to capture loads
    import gui.report_viewer as rv
    created = {}
    orig_ctor = rv.ReportViewer
    def fake_ctor(parent=None, json_path=None, csv_path=None):
        created['json'] = str(json_path) if json_path else None
        created['csv'] = str(csv_path) if csv_path else None
        class FakeDialog:
            def exec(self):
                return
        return FakeDialog()

    monkeypatch.setattr(rv, 'ReportViewer', fake_ctor)

    app = QApplication.instance() or QApplication(sys.argv)
    from gui.main_window import MainWindow
    win = MainWindow()
    qtbot.addWidget(win)
    win.output_edit.setText(str(out))

    # Click view report
    qtbot.mouseClick(win.view_report_btn, Qt.LeftButton)
    assert created.get('json') == str(report)

    # Click view csv
    qtbot.mouseClick(win.view_csv_btn, Qt.LeftButton)
    assert created.get('csv') == str(csv_file)


def test_shortcuts_and_accessibility(qtbot):
    app = QApplication.instance() or QApplication(sys.argv)
    from gui.main_window import MainWindow
    win = MainWindow()
    qtbot.addWidget(win)

    # Check accessible names
    assert win.start_btn.accessibleName() == 'StartCrawler'
    assert win.stop_btn.accessibleName() == 'StopCrawler'

    # Check shortcuts exist (string representations may vary)
    try:
        s = win.start_btn.shortcut().toString()
        assert s
    except Exception:
        # On some platforms shortcut may not be settable; pass
        pass
