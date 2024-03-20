from typing import Optional

import matplotlib.pyplot as plt
import scienceplots  # noqa
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import \
    NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from PyQt6.QtWidgets import QWidget  # pylint: disable=no-name-in-module

from core.logger_config import logger

# Применяем стили scienceplots
plt.style.use(['science', 'no-latex', 'nature', 'grid'])


class PlotCanvas(FigureCanvas):

    def __init__(self, parent: Optional[QWidget] = None, width: float = 5, height: float = 4, dpi: int = 100):
        fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = fig.add_subplot(111)
        super().__init__(fig)
        self.setParent(parent)

        self.toolbar = NavigationToolbar(self, parent)
        self.plot()

    def plot(self, data=None):
        logger.debug("Перерисовка графика")
        if data is None:
            data = [1, 2, 3, 4, 5]  # Тестовые данные
        self.axes.plot(data, 'r-')
        self.draw()
