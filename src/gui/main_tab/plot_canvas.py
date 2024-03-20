from typing import Optional

# Применяем стили scienceplots
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import \
    NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from PyQt6.QtCore import pyqtSlot
from PyQt6.QtWidgets import QVBoxLayout, QWidget

from src.logger_config import logger
from src.logger_console import LoggerConsole as console

plt.style.use(['science', 'no-latex', 'nature', 'grid'])

class PlotCanvas(QWidget):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        self.axes = self.figure.add_subplot(111)

        self.toolbar = NavigationToolbar(self.canvas, self)

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        self.layout.addWidget(self.toolbar)
        self.layout.addWidget(self.canvas)

        self.mock_plot()

    def mock_plot(self, data=None):
        logger.debug("Перерисовка графика")
        if data is None:
            data = [1, 2, 3, 4, 5]
        self.axes.plot(data)
        self.figure.tight_layout()
        self.canvas.draw()

    def add_plot(self, x, y, label: str):
        logger.debug(f"Добавление кривой: {label}")
        console.log(f"Добавление кривой: {label}")
        self.axes.plot(x, y, label=label)
        self.figure.tight_layout()
        self.canvas.draw()

    @pyqtSlot(pd.DataFrame)
    def plot_from_dataframe(self, data: pd.DataFrame):
        self.axes.clear()
        logger.debug("Оси очищены от кривых")
        if 'temperature' in data.columns:
            x = data['temperature']
            for column in data.columns:
                if column != 'temperature':
                    self.add_plot(x, data[column], label=column)
        else:
            logger.error("В DataFrame отсутствует столбец 'temperature' для оси X")
            console.log("В файле отсутствует столбец 'temperature' для оси X")
        self.canvas.draw()
