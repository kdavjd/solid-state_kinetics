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
from gui.main_tab.PlotCanvas.anchor_group import (HeightAnchorGroup,
                                                  PositionAnchorGroup)

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
        self.dragging_anchor = None

        self.canvas.mpl_connect('draw_event', self.on_draw)
        self.canvas.mpl_connect('button_press_event', self.on_click)
        self.canvas.mpl_connect('button_release_event', self.on_release)
        self.canvas.mpl_connect('motion_notify_event', self.on_motion)

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

    def determine_line_properties(self, reaction_name):
        if "cumulative_upper_bound" in reaction_name or "cumulative_lower_bound" in reaction_name:
            return {'linewidth': 0.1, 'linestyle': '-', 'color': 'grey'}
        elif "cumulative_coeffs" in reaction_name:
            return {'linewidth': 1, 'linestyle': 'dotted'}
        elif "upper_bound_coeffs" in reaction_name or "lower_bound_coeffs" in reaction_name:
            return {'linewidth': 1.25, 'linestyle': '-.'}
        else:
            return {}

    def update_fill_between(self):
        if 'cumulative_upper_bound_coeffs' in self.lines and 'cumulative_lower_bound_coeffs' in self.lines:
            x = self.lines['cumulative_upper_bound_coeffs'].get_xdata()
            upper_y = self.lines['cumulative_upper_bound_coeffs'].get_ydata()
            lower_y = self.lines['cumulative_lower_bound_coeffs'].get_ydata()
            self.axes.fill_between(x, lower_y, upper_y, color='grey', alpha=0.1)

        if 'upper_bound_coeffs' in self.lines and 'lower_bound_coeffs' in self.lines:
            x = self.lines['upper_bound_coeffs'].get_xdata()
            upper_y = self.lines['upper_bound_coeffs'].get_ydata()
            lower_y = self.lines['lower_bound_coeffs'].get_ydata()
            self.axes.fill_between(x, lower_y, upper_y, color='grey', alpha=0.1)

    @pyqtSlot(tuple, list)
    def plot_reaction(self, keys, values):
        file_name, reaction_name = keys
        x, y = values
        if reaction_name in self.lines:
            line = self.lines[reaction_name]
            line.remove()
            del self.lines[reaction_name]

        line_properties = self.determine_line_properties(reaction_name)
        self.add_or_update_line(reaction_name, x, y, **line_properties)

        if any(bound in reaction_name for bound in ['upper_bound', 'lower_bound']):
            self.update_fill_between()

    @pyqtSlot(dict)
    def add_anchors(self, reaction_data: dict):
        logger.info(f"Пришли данные: {reaction_data}")

        self.position_anchor_groups = {}
        self.height_anchor_groups = {}

        center_params = reaction_data['coeffs'][2]
        upper_params = reaction_data['upper_bound_coeffs'][2]
        lower_params = reaction_data['lower_bound_coeffs'][2]

        center_position_group = PositionAnchorGroup(
            self.axes, center_params, upper_params, lower_params
        )
        height_position_group = HeightAnchorGroup(
            self.axes, center_params, upper_params, lower_params
        )

        self.position_anchor_groups['coeffs'] = center_position_group
        self.height_anchor_groups['coeffs'] = height_position_group

        self.canvas.draw_idle()
        self.figure.tight_layout()

    def find_dragging_anchor(self, event, anchor_groups):
        for group in anchor_groups.values():
            if group.center.contains(event)[0]:
                return group.center
            elif group.upper_bound.contains(event)[0] or group.lower_bound.contains(event)[0]:
                return group.upper_bound if group.upper_bound.contains(event)[0] else group.lower_bound
        return None

    def log_anchor_positions(self, anchor_groups):
        for group in anchor_groups.values():
            group.log_anchor_positions()

    def update_anchor_position(self, event, anchor_groups, axis):
        for group in anchor_groups.values():
            if self.dragging_anchor == group.center:
                if axis == 'x':
                    group.set_center_position(event.xdata)
                else:
                    group.set_center_position(event.ydata)
            elif self.dragging_anchor in [group.upper_bound, group.lower_bound]:
                if axis == 'x':
                    group.set_bound_position(self.dragging_anchor, event.xdata)
                else:
                    group.set_bound_position(self.dragging_anchor, event.ydata)

    def on_click(self, event):
        logger.debug(f"Событие нажатия мыши: {event}")
        if event.inaxes != self.axes:
            return

        self.dragging_anchor = self.find_dragging_anchor(event, self.position_anchor_groups)
        if not self.dragging_anchor:
            self.dragging_anchor = self.find_dragging_anchor(event, self.height_anchor_groups)

    def on_release(self, event):
        logger.debug(f"Событие отпуска мыши: {event}")
        self.dragging_anchor = None

        self.log_anchor_positions(self.position_anchor_groups)
        self.log_anchor_positions(self.height_anchor_groups)

    def on_motion(self, event):
        if self.dragging_anchor is None or event.inaxes != self.axes:
            return

        self.update_anchor_position(event, self.position_anchor_groups, 'x')
        self.update_anchor_position(event, self.height_anchor_groups, 'y')

        self.canvas.draw_idle()
        self.figure.tight_layout()
