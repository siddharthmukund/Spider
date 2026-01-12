from PySide6.QtWidgets import QWidget, QVBoxLayout
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


class Sparkline(QWidget):
    """A small sparkline plot for response time history."""
    def __init__(self, parent=None, width=3, height=0.6, dpi=100):
        super().__init__(parent)
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.canvas = FigureCanvas(self.fig)
        self.ax = self.fig.add_subplot(111)
        self.ax.set_axis_off()
        self.x = []
        self.y = []

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.canvas)
        self.setLayout(layout)

    def update_data(self, values):
        self.x = list(range(len(values)))
        self.y = values[-50:]
        self.ax.clear()
        self.ax.plot(self.y, color='#1f77b4', linewidth=1)
        self.ax.fill_between(range(len(self.y)), self.y, color='#1f77b4', alpha=0.1)
        self.ax.set_axis_off()
        self.canvas.draw_idle()
