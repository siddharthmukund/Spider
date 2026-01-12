from PySide6.QtWidgets import QApplication
import sys


def test_focus_styles_applied(qtbot):
    app = QApplication.instance() or QApplication(sys.argv)
    from gui.main_window import MainWindow
    win = MainWindow()
    qtbot.addWidget(win)
    # App stylesheet should include focus rules
    stylesheet = app.styleSheet() or ''
    assert 'QLineEdit:focus' in stylesheet or 'QWidget:focus' in stylesheet
