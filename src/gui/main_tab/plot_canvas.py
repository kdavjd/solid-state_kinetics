from typing import Dict, Optional

import matplotlib.pyplot as plt
import pandas as pd
# see: https://pypi.org/project/SciencePlots/
import scienceplots  # noqa pylint: disable=unused-import
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import \
    NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from PyQt6.QtCore import pyqtSlot
from PyQt6.QtWidgets import QVBoxLayout, QWidget

from core.logger_config import logger
from core.logger_console import LoggerConsole as console

plt.style.use(['science', 'no-latex', 'nature', 'grid'])


class PlotCanvas(QWidget):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        self.axes = self.figure.add_subplot(111)

        self.toolbar = NavigationToolbar(self.canvas, self)
        self.lines: Dict[str, Line2D] = {}

        layout = QVBoxLayout()
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)
        self.setLayout(layout)

        self.background = None
        self.canvas.mpl_connect('draw_event', self.on_draw)

        self.mock_plot()

    def on_draw(self, event):
        """ Захватываем фон после первой отрисовки. """
        self.background = self.canvas.copy_from_bbox(self.figure.bbox)

    def restore_background(self):
        """ Восстанавливаем сохраненный фон. """
        self.canvas.restore_region(self.background)

    def mock_plot(self, data=None):
        if data is None:
            data = [1, 2, 3, 4, 5]
        self.add_or_update_line('mock', range(len(data)), data)

    def add_or_update_line(self, key, x, y, **kwargs):
        """ Добавляет или обновляет линию по ключу. """
        if key in self.lines:
            line = self.lines[key]
            line.set_data(x, y)
        else:
            line, = self.axes.plot(x, y, **kwargs)
            self.lines[key] = line
        self.canvas.draw_idle()
        self.figure.tight_layout()

    def plot_file_data_from_dataframe(self, data: pd.DataFrame):
        self.axes.clear()
        self.lines.clear()
        if 'temperature' in data.columns:
            x = data['temperature']
            for column in data.columns:
                if column != 'temperature':
                    self.add_or_update_line(column, x, data[column], label=column)
        else:
            logger.error(
                "В DataFrame отсутствует столбец 'temperature' для оси X")
            console.log("В файле отсутствует столбец 'temperature' для оси X")

    @pyqtSlot(tuple, list)
    def plot_reaction(self, keys, values):
        file_name, reaction_name = keys
        x, y = values
        if reaction_name in self.lines:
            line = self.lines[reaction_name]
            line.remove()
            del self.lines[reaction_name]

        if "cumulative" in reaction_name:
            self.add_or_update_line(
                reaction_name, x, y, linestyle='-.', color='red', linewidth=0.5, label=reaction_name)

            if 'cumulative_upper_bound' in self.lines and 'cumulative_lower_bound' in self.lines:
                upper_y = self.lines['cumulative_upper_bound'].get_ydata()
                lower_y = self.lines['cumulative_lower_bound'].get_ydata()
                self.axes.fill_between(x, lower_y, upper_y, color='grey', alpha=0.1)
        else:
            self.add_or_update_line(reaction_name, x, y, label=reaction_name)
