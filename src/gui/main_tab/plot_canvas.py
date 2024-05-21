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


class AnchorGroup:
    def __init__(self, axes, center_params, upper_params, lower_params):
        self.axes = axes
        h_center, z_center, w_center = center_params[:3]
        h_upper, z_upper, w_upper = upper_params[:3]
        h_lower, z_lower, w_lower = lower_params[:3]

        self.center, = self.axes.plot(z_center, h_center, 'ko', picker=5)
        self.upper_bound, = self.axes.plot(z_upper, h_upper, 'ro', picker=5)
        self.lower_bound, = self.axes.plot(z_lower, h_lower, 'ro', picker=5)

    def set_center_position(self, x, y):
        dx = x - self.center.get_xdata()[0]
        dy = y - self.center.get_ydata()[0]

        self.center.set_xdata(x)
        self.center.set_ydata(y)

        self.upper_bound.set_xdata(self.upper_bound.get_xdata()[0] + dx)
        self.upper_bound.set_ydata(self.upper_bound.get_ydata()[0] + dy)
        self.lower_bound.set_xdata(self.lower_bound.get_xdata()[0] + dx)
        self.lower_bound.set_ydata(self.lower_bound.get_ydata()[0] + dy)

    def set_bound_position(self, bound, x, y):
        if bound == self.upper_bound and y <= self.center.get_ydata()[0]:
            y = self.center.get_ydata()[0] + 0.1
        elif bound == self.lower_bound and y >= self.center.get_ydata()[0]:
            y = self.center.get_ydata()[0] - 0.1

        bound.set_xdata(x)
        bound.set_ydata(y)

        if bound == self.upper_bound:
            opposite_bound = self.lower_bound
            dy = y - self.center.get_ydata()[0]
        else:
            opposite_bound = self.upper_bound
            dy = self.center.get_ydata()[0] - y

        opposite_bound.set_xdata(x)
        opposite_bound.set_ydata(self.center.get_ydata()[0] - dy)

    def log_anchor_positions(self):
        logger.debug(f"Center: x={self.center.get_xdata()[0]}, y={self.center.get_ydata()[0]}")
        logger.debug(f"Upper bound: x={self.upper_bound.get_xdata()[0]}, y={self.upper_bound.get_ydata()[0]}")
        logger.debug(f"Lower bound: x={self.lower_bound.get_xdata()[0]}, y={self.lower_bound.get_ydata()[0]}")


class PositionAnchorGroup(AnchorGroup):
    def __init__(self, axes, center_params, upper_params, lower_params):
        h_center, z_center, w_center = center_params[:3]
        h_upper, z_upper, w_upper = upper_params[:3]
        h_lower, z_lower, w_lower = lower_params[:3]

        # Override y values to be 0 for PositionAnchorGroup
        super().__init__(axes, (0, z_center, w_center), (0, z_upper, w_upper), (0, z_lower, w_lower))

    def set_center_position(self, x):
        dx = x - self.center.get_xdata()[0]

        self.center.set_xdata(x)
        self.center.set_ydata(0)

        self.upper_bound.set_xdata(self.upper_bound.get_xdata()[0] + dx)
        self.upper_bound.set_ydata(0)
        self.lower_bound.set_xdata(self.lower_bound.get_xdata()[0] + dx)
        self.lower_bound.set_ydata(0)

    def set_bound_position(self, bound, x):
        if bound == self.upper_bound and x <= self.center.get_xdata()[0]:
            x = self.center.get_xdata()[0] + 0.1
        elif bound == self.lower_bound and x >= self.center.get_xdata()[0]:
            x = self.center.get_xdata()[0] - 0.1

        bound.set_xdata(x)
        bound.set_ydata(0)

        if bound == self.upper_bound:
            opposite_bound = self.lower_bound
            dx = x - self.center.get_xdata()[0]
        else:
            opposite_bound = self.upper_bound
            dx = self.center.get_xdata()[0] - x

        opposite_bound.set_xdata(self.center.get_xdata()[0] - dx)
        opposite_bound.set_ydata(0)


class HeightAnchorGroup(AnchorGroup):
    def __init__(self, axes, center_params, upper_params, lower_params):
        super().__init__(axes, center_params, upper_params, lower_params)

    def set_center_position(self, y):
        super().set_center_position(self.center.get_xdata()[0], y)

    def set_bound_position(self, bound, y):
        super().set_bound_position(bound, bound.get_xdata()[0], y)


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

    def on_click(self, event):
        logger.info(f"Click event: {event}")
        if event.inaxes != self.axes:
            return

        for group in self.position_anchor_groups.values():
            if group.center.contains(event)[0]:
                self.dragging_anchor = group.center
                logger.info(f"Dragging position anchor: {self.dragging_anchor}")
                break
            elif group.upper_bound.contains(event)[0] or group.lower_bound.contains(event)[0]:
                self.dragging_anchor = group.upper_bound if group.upper_bound.contains(event)[0] else group.lower_bound
                logger.info(f"Dragging bound anchor: {self.dragging_anchor}")
                break

        for group in self.height_anchor_groups.values():
            if group.center.contains(event)[0]:
                self.dragging_anchor = group.center
                logger.info(f"Dragging height anchor: {self.dragging_anchor}")
                break
            elif group.upper_bound.contains(event)[0] or group.lower_bound.contains(event)[0]:
                self.dragging_anchor = group.upper_bound if group.upper_bound.contains(event)[0] else group.lower_bound
                logger.info(f"Dragging bound anchor: {self.dragging_anchor}")
                break

    def on_release(self, event):
        logger.info(f"Release event: {event}")
        self.dragging_anchor = None

        for group in self.position_anchor_groups.values():
            group.log_anchor_positions()
        for group in self.height_anchor_groups.values():
            group.log_anchor_positions()

    def on_motion(self, event):
        logger.debug(f"Событие передвижения мыши: {event}")
        if self.dragging_anchor is None or event.inaxes != self.axes:
            return

        for group in self.position_anchor_groups.values():
            if self.dragging_anchor == group.center:
                group.set_center_position(event.xdata)
            elif self.dragging_anchor in [group.upper_bound, group.lower_bound]:
                group.set_bound_position(self.dragging_anchor, event.xdata)

        for group in self.height_anchor_groups.values():
            if self.dragging_anchor == group.center:
                group.set_center_position(event.ydata)
            elif self.dragging_anchor in [group.upper_bound, group.lower_bound]:
                group.set_bound_position(self.dragging_anchor, event.ydata)

        self.canvas.draw_idle()
        self.figure.tight_layout()
