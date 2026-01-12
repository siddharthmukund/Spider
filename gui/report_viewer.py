from PySide6.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QLabel, QTabWidget, QWidget, QTableWidget, QTableWidgetItem
from pathlib import Path
import json
import csv


class ReportViewer(QDialog):
    def __init__(self, parent=None, json_path: str = None, csv_path: str = None):
        super().__init__(parent)
        self.setWindowTitle('Report Viewer')
        self.resize(600, 400)

        layout = QVBoxLayout()
        tabs = QTabWidget()

        # JSON Tab
        self.json_tab = QWidget()
        self.json_layout = QVBoxLayout()
        self.json_summary = QLabel('No report loaded')
        self.json_text = QTextEdit()
        self.json_text.setReadOnly(True)
        self.json_layout.addWidget(self.json_summary)
        self.json_layout.addWidget(self.json_text)
        self.json_tab.setLayout(self.json_layout)
        tabs.addTab(self.json_tab, 'JSON')

        # CSV Tab
        self.csv_tab = QWidget()
        self.csv_layout = QVBoxLayout()
        self.csv_table = QTableWidget(0, 0)
        self.csv_layout.addWidget(self.csv_table)
        self.csv_tab.setLayout(self.csv_layout)
        tabs.addTab(self.csv_tab, 'CSV')

        # Pages tab (paginated view of JSON pages)
        self.pages_tab = QWidget()
        self.pages_layout = QVBoxLayout()
        # Filters
        from PySide6.QtWidgets import QHBoxLayout, QLineEdit, QComboBox, QSpinBox, QPushButton
        from PySide6.QtGui import QKeySequence
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel('Filter URL:'))
        self.url_filter = QLineEdit(self.pages_tab)
        self.url_filter.setAccessibleName('URLFilter')
        self.url_filter.setAccessibleDescription('Filter pages by URL substring')
        filter_layout.addWidget(self.url_filter)
        filter_layout.addWidget(QLabel('Status:'))
        self.status_filter = QComboBox(self.pages_tab)
        self.status_filter.addItem('All')
        self.status_filter.addItem('200')
        self.status_filter.addItem('404')
        self.status_filter.addItem('500')
        self.status_filter.setAccessibleName('StatusFilter')
        filter_layout.addWidget(self.status_filter)
        filter_layout.addWidget(QLabel('Page size:'))
        self.page_size_spin = QSpinBox(self.pages_tab)
        self.page_size_spin.setRange(1, 1000)
        self.page_size_spin.setValue(50)
        self.page_size_spin.setAccessibleName('PageSize')
        filter_layout.addWidget(self.page_size_spin)
        self.filter_btn = QPushButton('Apply', self.pages_tab)
        self.filter_btn.setAccessibleName('ApplyFilters')
        self.filter_btn.setAccessibleDescription('Apply filters to pages')
        try:
            self.filter_btn.setShortcut(QKeySequence('Ctrl+F'))
        except Exception:
            pass
        filter_layout.addWidget(self.filter_btn)
        self.prev_btn = QPushButton('Prev', self.pages_tab)
        self.prev_btn.setAccessibleName('PrevPage')
        self.next_btn = QPushButton('Next', self.pages_tab)
        self.next_btn.setAccessibleName('NextPage')
        try:
            self.prev_btn.setShortcut(QKeySequence('Left'))
            self.next_btn.setShortcut(QKeySequence('Right'))
        except Exception:
            pass
        self.page_label = QLabel('Page 0/0')
        filter_layout.addWidget(self.prev_btn)
        filter_layout.addWidget(self.next_btn)
        filter_layout.addWidget(self.page_label)
        self.pages_layout.addLayout(filter_layout)

        # Pages table
        self.pages_table = QTableWidget(0, 3)
        self.pages_table.setHorizontalHeaderLabels(['URL', 'Response (s)', 'Status'])
        self.pages_layout.addWidget(self.pages_table)

        # Export filtered CSV button
        self.export_filtered_btn = QPushButton('Export Filtered CSV')
        self.pages_layout.addWidget(self.export_filtered_btn)

        self.pages_tab.setLayout(self.pages_layout)
        tabs.addTab(self.pages_tab, 'Pages')

        # Action buttons (Save snapshot / Export CSV)
        from PySide6.QtWidgets import QHBoxLayout, QPushButton
        action_layout = QHBoxLayout()
        self.save_snapshot_btn = QPushButton('Save Snapshot')
        self.export_csv_btn = QPushButton('Export CSV')
        action_layout.addWidget(self.save_snapshot_btn)
        action_layout.addWidget(self.export_csv_btn)
        layout.addLayout(action_layout)

        self.setLayout(layout)

        # Internal storage for loaded data
        self._json_data = None
        self._csv_rows = []
        self._filtered_pages = []
        self._current_page = 0

        # Connect actions
        self.save_snapshot_btn.clicked.connect(self.save_snapshot)
        self.export_csv_btn.clicked.connect(self.export_csv)
        self.filter_btn.clicked.connect(self.apply_filters)
        self.prev_btn.clicked.connect(self.prev_page)
        self.next_btn.clicked.connect(self.next_page)
        self.export_filtered_btn.clicked.connect(self.export_filtered_csv)

        if json_path:
            self.load_json(json_path)
        if csv_path:
            self.load_csv(csv_path)

    def load_json(self, path: str):
        try:
            p = Path(path)
            if not p.exists():
                self.json_summary.setText(f'Report not found: {path}')
                return
            data = json.loads(p.read_text(encoding='utf-8'))
            self._json_data = data
            # Prepare pages list for pagination
            pages = data.get('pages', {})
            self._filtered_pages = []
            for url, pd in pages.items():
                # pd expected to have response_time and status_code
                rt = pd.get('response_time', 0.0)
                sc = pd.get('status_code', 0)
                self._filtered_pages.append({'url': url, 'response_time': float(rt), 'status_code': int(sc)})
            self._current_page = 0

            meta = data.get('metadata', {})
            summary = data.get('summary', {})
            summary_text = f"Crawl date: {meta.get('crawl_date', '-')}, duration: {summary.get('duration_seconds', meta.get('duration_seconds', '-'))}s, pages: {summary.get('total_pages', '-')}, issues: {summary.get('total_issues', '-') }"
            self.json_summary.setText(summary_text)
            pretty = json.dumps(data, indent=2, ensure_ascii=False)
            self.json_text.setPlainText(pretty[:20000])  # limit size

            # Refresh pages table with default (no filters)
            self.apply_filters()
        except Exception as e:
            self.json_summary.setText(f'Error loading JSON: {e}')

    def save_snapshot(self):
        try:
            if not self._json_data:
                self.json_summary.setText('No JSON loaded to snapshot')
                return
            from PySide6.QtWidgets import QFileDialog
            opts = QFileDialog.Options()
            fname, _ = QFileDialog.getSaveFileName(self, 'Save JSON snapshot', 'report_snapshot.json', 'JSON Files (*.json);;All Files (*)', options=opts)
            if not fname:
                return
            with open(fname, 'w', encoding='utf-8') as f:
                json.dump(self._json_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.json_summary.setText(f'Error saving snapshot: {e}')

    def load_csv(self, path: str):
        try:
            p = Path(path)
            if not p.exists():
                return
            with open(p, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                rows = list(reader)
                if not rows:
                    return
                self._csv_rows = rows
                headers = rows[0]
                self.csv_table.setColumnCount(len(headers))
                self.csv_table.setHorizontalHeaderLabels(headers)
                self.csv_table.setRowCount(len(rows) - 1)
                for r, row in enumerate(rows[1:]):
                    for c, val in enumerate(row):
                        self.csv_table.setItem(r, c, QTableWidgetItem(val))
        except Exception:
            pass

    def export_csv(self):
        try:
            if not self._csv_rows:
                return
            from PySide6.QtWidgets import QFileDialog
            opts = QFileDialog.Options()
            fname, _ = QFileDialog.getSaveFileName(self, 'Export CSV', 'export.csv', 'CSV Files (*.csv);;All Files (*)', options=opts)
            if not fname:
                return
            # Write rows currently loaded (could be filtered view in the future)
            with open(fname, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                for row in self._csv_rows:
                    writer.writerow(row)
        except Exception:
            pass

    def _render_pages_page(self, page_index: int):
        # Render current page of filtered pages
        page_size = int(self.page_size_spin.value())
        total = len(self._filtered_pages)
        if total == 0:
            self.pages_table.setRowCount(0)
            self.page_label.setText('Page 0/0')
            return
        max_page = (total - 1) // page_size
        page_index = max(0, min(page_index, max_page))
        start = page_index * page_size
        end = min(start + page_size, total)
        subset = self._filtered_pages[start:end]
        self.pages_table.setRowCount(len(subset))
        for r, row in enumerate(subset):
            self.pages_table.setItem(r, 0, QTableWidgetItem(row['url']))
            self.pages_table.setItem(r, 1, QTableWidgetItem(f"{row['response_time']:.2f}"))
            self.pages_table.setItem(r, 2, QTableWidgetItem(str(row['status_code'])))
        self._current_page = page_index
        self.page_label.setText(f'Page {page_index + 1}/{max_page + 1}')

    def apply_filters(self):
        # Apply URL substring and status code filter
        term = self.url_filter.text().strip().lower()
        status = self.status_filter.currentText()
        out = []
        for p in getattr(self, '_filtered_pages', []):
            if term and term not in p['url'].lower():
                continue
            if status != 'All' and str(p['status_code']) != status:
                continue
            out.append(p)
        self._filtered_pages = out
        self._render_pages_page(0)

    def prev_page(self):
        self._render_pages_page(self._current_page - 1)

    def next_page(self):
        self._render_pages_page(self._current_page + 1)

    def export_filtered_csv(self):
        try:
            if not self._filtered_pages:
                return
            from PySide6.QtWidgets import QFileDialog
            opts = QFileDialog.Options()
            fname, _ = QFileDialog.getSaveFileName(self, 'Export Filtered CSV', 'filtered.csv', 'CSV Files (*.csv);;All Files (*)', options=opts)
            if not fname:
                return
            # Build rows: headers + filtered rows
            headers = ['url', 'response_time', 'status_code']
            with open(fname, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(headers)
                for row in self._filtered_pages:
                    writer.writerow([row['url'], f"{row['response_time']:.2f}", row['status_code']])
        except Exception:
            pass
