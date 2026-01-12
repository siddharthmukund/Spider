from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QSpinBox, QProgressBar, QTextEdit, QFileDialog
)
from PySide6.QtCore import Qt, Slot
from .worker import Worker


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('SEO Crawler GUI')
        self.resize(800, 600)

        self.worker = Worker()
        # Ensure focus styles exist even if run_gui.py wasn't used to start the app (tests)
        try:
            from PySide6.QtWidgets import QApplication
            app = QApplication.instance()
            if app and not app.styleSheet():
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
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        central = QWidget()
        layout = QVBoxLayout()

        # Config row
        cfg_layout = QHBoxLayout()
        cfg_layout.addWidget(QLabel('Base URL:'))
        self.base_url_edit = QLineEdit('https://example.com')
        cfg_layout.addWidget(self.base_url_edit)

        cfg_layout.addWidget(QLabel('Max pages:'))
        self.max_pages_spin = QSpinBox()
        self.max_pages_spin.setRange(1, 10000)
        self.max_pages_spin.setValue(100)
        cfg_layout.addWidget(self.max_pages_spin)

        cfg_layout.addWidget(QLabel('Workers:'))
        self.max_workers_spin = QSpinBox()
        self.max_workers_spin.setRange(1, 50)
        self.max_workers_spin.setValue(5)
        cfg_layout.addWidget(self.max_workers_spin)

        layout.addLayout(cfg_layout)

        # Output directory chooser
        out_layout = QHBoxLayout()
        out_layout.addWidget(QLabel('Output dir:'))
        self.output_edit = QLineEdit('seo_audit_output')
        out_layout.addWidget(self.output_edit)
        self.output_btn = QPushButton('Choose...')
        out_layout.addWidget(self.output_btn)
        layout.addLayout(out_layout)

        # Controls
        ctl_layout = QHBoxLayout()
        self.start_btn = QPushButton('Start')
        self.stop_btn = QPushButton('Stop')
        self.stop_btn.setEnabled(False)
        ctl_layout.addWidget(self.start_btn)
        ctl_layout.addWidget(self.stop_btn)

        # Report/actions buttons
        self.open_report_btn = QPushButton('Open Report')
        self.open_csv_btn = QPushButton('Open CSV')
        self.open_folder_btn = QPushButton('Open Folder')
        # In-app viewers
        self.view_report_btn = QPushButton('View Report')
        self.view_csv_btn = QPushButton('View CSV')
        ctl_layout.addWidget(self.open_report_btn)
        ctl_layout.addWidget(self.open_csv_btn)
        ctl_layout.addWidget(self.open_folder_btn)
        ctl_layout.addWidget(self.view_report_btn)
        ctl_layout.addWidget(self.view_csv_btn)

        # Accessibility labels
        self.start_btn.setAccessibleName('StartCrawler')
        self.start_btn.setAccessibleDescription('Start the crawl')
        self.stop_btn.setAccessibleName('StopCrawler')
        self.stop_btn.setAccessibleDescription('Stop the crawl')
        self.view_report_btn.setAccessibleName('ViewReport')
        self.view_report_btn.setAccessibleDescription('Open the in-app report viewer dialog')
        self.view_csv_btn.setAccessibleName('ViewCSV')
        self.view_csv_btn.setAccessibleDescription('Open the in-app CSV viewer dialog')

        layout.addLayout(ctl_layout)
        # Accessibility descriptions for form controls
        self.base_url_edit.setAccessibleDescription('The root URL to start crawling from')
        self.base_url_edit.setAccessibleName('BaseURL')
        self.max_pages_spin.setAccessibleDescription('Maximum number of pages to crawl')
        self.max_pages_spin.setAccessibleName('MaxPages')
        self.max_workers_spin.setAccessibleDescription('Number of worker threads for crawling')
        self.max_workers_spin.setAccessibleName('MaxWorkers')
        self.output_edit.setAccessibleDescription('Directory where output files will be saved')
        self.output_edit.setAccessibleName('OutputDir')
        self.output_btn.setAccessibleDescription('Choose output directory')
        self.output_btn.setAccessibleName('ChooseOutputDir')
        self.open_report_btn.setAccessibleDescription('Open the generated JSON report in default application')
        self.open_report_btn.setAccessibleName('OpenJSONReport')
        self.open_csv_btn.setAccessibleDescription('Open the generated CSV in default application')
        self.open_csv_btn.setAccessibleName('OpenCSV')
        self.open_folder_btn.setAccessibleDescription('Open the output directory in file explorer')
        self.open_folder_btn.setAccessibleName('OpenFolder')

        # Progress
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        layout.addWidget(self.progress)

        # Live metrics panel (avg/fastest/slowest/ETA)
        metrics_layout = QHBoxLayout()
        self.avg_label = QLabel('Avg: 0.00s')
        self.fastest_label = QLabel('Fastest: -')
        self.slowest_label = QLabel('Slowest: -')
        self.eta_label = QLabel('ETA: -')
        metrics_layout.addWidget(self.avg_label)
        metrics_layout.addWidget(self.fastest_label)
        metrics_layout.addWidget(self.slowest_label)
        metrics_layout.addWidget(self.eta_label)

        # Sparkline
        from .sparkline import Sparkline
        self.spark = Sparkline()
        metrics_layout.addWidget(self.spark)

        layout.addLayout(metrics_layout)

        # Per-page metrics table
        from PySide6.QtWidgets import QTableWidget, QTableWidgetItem
        layout.addWidget(QLabel('Recent Pages:'))
        self.metrics_table = QTableWidget(0, 3)
        self.metrics_table.setHorizontalHeaderLabels(['URL', 'Response (s)', 'Status'])
        layout.addWidget(self.metrics_table, 1)

        # Logs
        layout.addWidget(QLabel('Logs:'))
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        layout.addWidget(self.log_view, 1)

        central.setLayout(layout)
        self.setCentralWidget(central)

        # Set explicit tab order for keyboard navigation
        try:
            self.setTabOrder(self.base_url_edit, self.max_pages_spin)
            self.setTabOrder(self.max_pages_spin, self.max_workers_spin)
            self.setTabOrder(self.max_workers_spin, self.output_edit)
            self.setTabOrder(self.output_edit, self.output_btn)
            self.setTabOrder(self.output_btn, self.start_btn)
            self.setTabOrder(self.start_btn, self.stop_btn)
            self.setTabOrder(self.stop_btn, self.open_report_btn)
            self.setTabOrder(self.open_report_btn, self.view_report_btn)
            self.setTabOrder(self.view_report_btn, self.metrics_table)
            self.setTabOrder(self.metrics_table, self.log_view)
        except Exception:
            pass

    def _connect_signals(self):
        self.start_btn.clicked.connect(self.on_start)
        self.stop_btn.clicked.connect(self.on_stop)
        self.output_btn.clicked.connect(self.select_output_dir)

        # Report actions
        self.open_report_btn.clicked.connect(self.on_open_report)
        self.open_csv_btn.clicked.connect(self.on_open_csv)
        self.open_folder_btn.clicked.connect(self.on_open_folder)
        self.view_report_btn.clicked.connect(self.on_view_report)
        self.view_csv_btn.clicked.connect(self.on_view_csv)

        # Shortcuts
        try:
            from PySide6.QtGui import QKeySequence
            self.start_btn.setShortcut(QKeySequence('Ctrl+R'))
            self.stop_btn.setShortcut(QKeySequence('Ctrl+T'))
            self.open_report_btn.setShortcut(QKeySequence('Ctrl+O'))
            self.view_report_btn.setShortcut(QKeySequence('Ctrl+Shift+O'))
        except Exception:
            pass

        self.worker.log.connect(self.append_log)
        self.worker.finished.connect(self.on_finished)
        self.worker.error.connect(self.on_error)
        self.worker.progress.connect(self.on_progress)
        self.worker.metrics.connect(self.on_metrics)
        self.worker.eta.connect(self.on_eta)

    @Slot()
    def on_start(self):
        base = self.base_url_edit.text().strip()
        maxp = self.max_pages_spin.value()
        workers = self.max_workers_spin.value()
        out = self.output_edit.text().strip() or 'seo_audit_output'

        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.append_log('Starting crawl...')
        self.worker.start(base, maxp, workers, out)

    @Slot()
    def on_stop(self):
        self.worker.stop()
        self.append_log('Stop requested')
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

    @Slot(str)
    def append_log(self, message: str):
        self.log_view.append(message)

    @Slot(str)
    def on_finished(self, report_path: str):
        self.append_log(f'Crawl finished, report: {report_path}')
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

    @Slot(int, int)
    def on_progress(self, completed: int, total: int):
        try:
            if total:
                percent = int((completed / total) * 100)
                self.progress.setValue(percent)
                self.append_log(f'Progress: {completed}/{total} ({percent}%)')
        except Exception:
            pass

    @Slot(str, float, int)
    def on_metrics(self, url: str, response_time: float, status_code: int):
        try:
            # Update labels for live metrics
            cur_avg = float(self.worker._avg_response)
            fastest = self.worker._fastest if self.worker._fastest != float('inf') else None
            slowest = self.worker._slowest if self.worker._slowest != 0.0 else None
            self.avg_label.setText(f'Avg: {cur_avg:.2f}s')
            self.fastest_label.setText(f'Fastest: {fastest:.2f}s' if fastest is not None else 'Fastest: -')
            self.slowest_label.setText(f'Slowest: {slowest:.2f}s' if slowest is not None else 'Slowest: -')
            self.append_log(f'Page: {url} time={response_time:.2f}s status={status_code}')

            # Update per-page table (prepend latest)
            QTableWidgetItemClass = None
            try:
                from PySide6.QtWidgets import QTableWidgetItem
                QTableWidgetItemClass = QTableWidgetItem
            except Exception:
                QTableWidgetItemClass = None

            if QTableWidgetItemClass:
                self.metrics_table.insertRow(0)
                self.metrics_table.setItem(0, 0, QTableWidgetItem(url))
                self.metrics_table.setItem(0, 1, QTableWidgetItem(f"{response_time:.2f}"))
                self.metrics_table.setItem(0, 2, QTableWidgetItem(str(status_code)))
                # Limit rows
                while self.metrics_table.rowCount() > 50:
                    self.metrics_table.removeRow(self.metrics_table.rowCount() - 1)

            # Update sparkline
            try:
                # gather response times from table
                vals = []
                for r in range(self.metrics_table.rowCount()):
                    it = self.metrics_table.item(r, 1)
                    if it:
                        try:
                            vals.append(float(it.text()))
                        except Exception:
                            pass
                self.spark.update_data(list(reversed(vals)))
            except Exception:
                pass
        except Exception:
            pass

    @Slot(float)
    def on_eta(self, seconds: float):
        try:
            if seconds is None:
                self.eta_label.setText('ETA: -')
            else:
                if seconds < 1:
                    txt = '<1s'
                else:
                    txt = f'{int(seconds)}s'
                self.eta_label.setText(f'ETA: {txt}')
        except Exception:
            pass

    @Slot(str)
    def on_error(self, err: str):
        self.append_log(f'Error: {err}')
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

    @Slot()
    def on_view_report(self):
        out = self.output_edit.text().strip() or 'seo_audit_output'
        from pathlib import Path
        report = Path(out) / 'seo_report.json'
        try:
            from .report_viewer import ReportViewer
            dlg = ReportViewer(self, json_path=str(report))
            dlg.exec()
        except Exception as e:
            self.append_log(f'Error opening report viewer: {e}')

    @Slot()
    def on_view_csv(self):
        out = self.output_edit.text().strip() or 'seo_audit_output'
        from pathlib import Path
        csv = Path(out) / 'seo_data.csv'
        try:
            from .report_viewer import ReportViewer
            dlg = ReportViewer(self, csv_path=str(csv))
            dlg.exec()
        except Exception as e:
            self.append_log(f'Error opening CSV viewer: {e}')

    def select_output_dir(self):
        dirpath = QFileDialog.getExistingDirectory(self, 'Select output directory', '.')
        if dirpath:
            self.output_edit.setText(dirpath)

    @Slot()
    def on_open_report(self):
        out = self.output_edit.text().strip() or 'seo_audit_output'
        from pathlib import Path
        report = Path(out) / 'seo_report.json'
        try:
            from .os_utils import open_path
            if not report.exists():
                self.append_log(f'Report not found: {report}')
                return
            ok = open_path(str(report))
            if not ok:
                self.append_log(f'Could not open report: {report}')
        except Exception as e:
            self.append_log(f'Error opening report: {e}')

    @Slot()
    def on_open_csv(self):
        out = self.output_edit.text().strip() or 'seo_audit_output'
        from pathlib import Path
        csv = Path(out) / 'seo_data.csv'
        try:
            from .os_utils import open_path
            if not csv.exists():
                self.append_log(f'CSV not found: {csv}')
                return
            ok = open_path(str(csv))
            if not ok:
                self.append_log(f'Could not open CSV: {csv}')
        except Exception as e:
            self.append_log(f'Error opening CSV: {e}')

    @Slot()
    def on_open_folder(self):
        out = self.output_edit.text().strip() or 'seo_audit_output'
        from pathlib import Path
        folder = Path(out)
        try:
            from .os_utils import open_path
            if not folder.exists():
                self.append_log(f'Folder not found: {folder}')
                return
            ok = open_path(str(folder))
            if not ok:
                self.append_log(f'Could not open folder: {folder}')
        except Exception as e:
            self.append_log(f'Error opening folder: {e}')
