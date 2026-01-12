import sys
from PySide6.QtWidgets import QApplication
from gui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    # Focus indicator style for accessibility (explicit controls)
    try:
        app.setStyleSheet('''
            QLineEdit:focus, QPushButton:focus, QSpinBox:focus, QTableWidget:focus {
                border: 2px solid #0078D4;
                outline: none;
            }
            QPushButton:focus {
                background-color: #e6f0fb;
            }
        ''')
    except Exception:
        pass
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
