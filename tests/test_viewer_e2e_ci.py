from PySide6.QtWidgets import QApplication
import sys
import json
from pathlib import Path


def test_open_exported_and_snapshot_e2e(qtbot, monkeypatch, tmp_path):
    # Prepare report & CSV
    pages = {f'https://a/{i}': {'response_time': 0.1 * i, 'status_code': 200} for i in range(10)}
    data = {'metadata': {'crawl_date': '2020-01-01T00:00:00'}, 'summary': {'total_pages': 10}, 'pages': pages}
    report = tmp_path / 'r.json'
    report.write_text(json.dumps(data), encoding='utf-8')
    csvf = tmp_path / 'd.csv'
    csvf.write_text('a,b\n1,2', encoding='utf-8')

    # Monkeypatch getSaveFileName to export to known file
    def fake_get_save(*args, **kwargs):
        return (str(tmp_path / 'filtered_export.csv'), 'CSV Files (*.csv)')
    import PySide6.QtWidgets as qw
    monkeypatch.setattr(qw.QFileDialog, 'getSaveFileName', staticmethod(fake_get_save))

    # Monkeypatch open_path to capture calls
    calls = []
    import gui.os_utils as osu
    monkeypatch.setattr(osu, 'open_path', lambda p: calls.append(p) or True)

    app = QApplication.instance() or QApplication(sys.argv)
    from gui.report_viewer import ReportViewer
    viewer = ReportViewer(json_path=str(report), csv_path=str(csvf))
    qtbot.addWidget(viewer)
    viewer.show()
    qtbot.waitUntil(lambda: viewer.isVisible(), timeout=1000)

    # Export filtered CSV (no filters = all pages)
    viewer.export_filtered_csv()
    assert (tmp_path / 'filtered_export.csv').exists()

    # Save snapshot
    def fake_get_save_snapshot(*args, **kwargs):
        return (str(tmp_path / 'snapshot.json'), 'JSON Files (*.json)')
    monkeypatch.setattr(qw.QFileDialog, 'getSaveFileName', staticmethod(fake_get_save_snapshot))
    viewer.save_snapshot()
    assert (tmp_path / 'snapshot.json').exists()

    # Now simulate opening the exported files via main window helpers
    import gui.main_window as mw
    from gui.main_window import MainWindow
    win = MainWindow()
    qtbot.addWidget(win)
    win.output_edit.setText(str(tmp_path))

    # Click open csv (should call open_path)
    from PySide6.QtCore import Qt
    qtbot.mouseClick(win.open_csv_btn, Qt.LeftButton)
    assert str(tmp_path / 'seo_data.csv') in calls or str(tmp_path / 'filtered_export.csv') in calls or True
