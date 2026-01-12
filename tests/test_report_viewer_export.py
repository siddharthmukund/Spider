from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
import sys
import json
from pathlib import Path


def test_save_snapshot_and_export_csv(qtbot, monkeypatch, tmp_path):
    # Prepare sample JSON and CSV
    json_data = {'metadata': {'crawl_date': '2020-01-01T00:00:00'}, 'summary': {'total_pages': 1}}
    json_file = tmp_path / 'report.json'
    json_file.write_text(json.dumps(json_data), encoding='utf-8')

    csv_file = tmp_path / 'data.csv'
    csv_file.write_text('a,b\n1,2', encoding='utf-8')

    # Monkeypatch file dialogs to return paths
    def fake_get_save_json(*args, **kwargs):
        return (str(tmp_path / 'snapshot.json'), 'JSON Files (*.json)')

    def fake_get_save_csv(*args, **kwargs):
        return (str(tmp_path / 'export.csv'), 'CSV Files (*.csv)')

    import PySide6.QtWidgets as qw
    monkeypatch.setattr(qw.QFileDialog, 'getSaveFileName', staticmethod(fake_get_save_json))

    # Open viewer
    app = QApplication.instance() or QApplication(sys.argv)
    from gui.report_viewer import ReportViewer
    viewer = ReportViewer(json_path=str(json_file), csv_path=str(csv_file))
    qtbot.addWidget(viewer)
    viewer.show()
    qtbot.waitUntil(lambda: viewer.isVisible(), timeout=1000)

    # Save snapshot
    qtbot.mouseClick(viewer.save_snapshot_btn, Qt.LeftButton)
    snap = tmp_path / 'snapshot.json'
    assert snap.exists()
    assert json.loads(snap.read_text(encoding='utf-8')) == json_data

    # Export CSV
    monkeypatch.setattr(qw.QFileDialog, 'getSaveFileName', staticmethod(fake_get_save_csv))
    qtbot.mouseClick(viewer.export_csv_btn, Qt.LeftButton)
    exp = tmp_path / 'export.csv'
    assert exp.exists()
    content = exp.read_text(encoding='utf-8')
    assert 'a,b' in content
