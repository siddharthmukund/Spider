from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
import sys


def test_tab_order_and_accessible_descriptions(qtbot):
    app = QApplication.instance() or QApplication(sys.argv)
    from gui.main_window import MainWindow
    win = MainWindow()
    qtbot.addWidget(win)
    win.show()
    qtbot.waitUntil(lambda: win.isVisible(), timeout=1000)

    # Ensure descriptions and names exist
    assert win.base_url_edit.accessibleDescription() != ''
    assert win.max_pages_spin.accessibleDescription() != ''
    assert win.base_url_edit.accessibleName() != ''
    assert win.max_pages_spin.accessibleName() != ''

    # Verify widgets can accept focus (tab navigation should be possible)
    assert win.base_url_edit.focusPolicy() != Qt.NoFocus
    assert win.max_pages_spin.focusPolicy() != Qt.NoFocus
    assert win.start_btn.focusPolicy() != Qt.NoFocus

    # Basic keyboard-only flow: tab to start/stop and trigger via shortcuts
    win.activateWindow()
    win.raise_()
    qtbot.waitUntil(lambda: win.isActiveWindow(), timeout=1000)
    win.base_url_edit.setFocus()
    qtbot.waitUntil(lambda: win.base_url_edit.hasFocus(), timeout=1000)
    qtbot.keyClick(win, Qt.Key_Tab)
    qtbot.waitUntil(lambda: win.max_pages_spin.hasFocus(), timeout=1000)
    assert win.max_pages_spin.hasFocus()
