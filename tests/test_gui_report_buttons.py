from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
import sys
from pathlib import Path


def test_open_buttons_call_os_utils(qtbot, monkeypatch, tmp_path):
    # Create dummy report and csv
    out = tmp_path / 'out'
    out.mkdir()
    (out / 'seo_report.json').write_text('{}', encoding='utf-8')
    (out / 'seo_data.csv').write_text('a,b\n1,2', encoding='utf-8')

    # Track calls
    calls = []
    def fake_open(p):
        calls.append(p)
        return True

    import gui.os_utils as osu
    monkeypatch.setattr(osu, 'open_path', fake_open)

    app = QApplication.instance() or QApplication(sys.argv)
    from gui.main_window import MainWindow
    win = MainWindow()
    qtbot.addWidget(win)

    win.output_edit.setText(str(out))

    # Click open report
    qtbot.mouseClick(win.open_report_btn, Qt.LeftButton)
    assert str(out / 'seo_report.json') in calls

    # Click open csv
    qtbot.mouseClick(win.open_csv_btn, Qt.LeftButton)
    assert str(out / 'seo_data.csv') in calls

    # Click open folder
    qtbot.mouseClick(win.open_folder_btn, Qt.LeftButton)
    assert str(out) in calls


def test_open_buttons_handle_missing_files(qtbot, monkeypatch, tmp_path):
    out = tmp_path / 'out'
    out.mkdir()

    app = QApplication.instance() or QApplication(sys.argv)
    from gui.main_window import MainWindow
    win = MainWindow()
    qtbot.addWidget(win)

    win.output_edit.setText(str(out))

    # No files exist, clicking should append log messages and not raise
    qtbot.mouseClick(win.open_report_btn, Qt.LeftButton)
    qtbot.mouseClick(win.open_csv_btn, Qt.LeftButton)
    qtbot.mouseClick(win.open_folder_btn, Qt.LeftButton)

    txt = win.log_view.toPlainText()
    assert 'not found' in txt or 'Could not open' in txt