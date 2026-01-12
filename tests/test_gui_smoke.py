from gui.main_window import MainWindow
from PySide6.QtWidgets import QApplication
import sys


def test_main_window_instantiation(qtbot):
    app = QApplication.instance() or QApplication(sys.argv)
    win = MainWindow()
    qtbot.addWidget(win)
    assert win.windowTitle() == 'SEO Crawler GUI'
