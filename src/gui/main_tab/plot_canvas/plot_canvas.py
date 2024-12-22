from typing import Dict, Optional

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd

# see: https://pypi.org/project/SciencePlots/
import scienceplots  # noqa pylint: disable=unused-import
from core.logger_config import logger
from core.logger_console import LoggerConsole as console
from gui.main_tab.plot_canvas.anchor_group import HeightAnchorGroup, PositionAnchorGroup
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from PyQt6.QtCore import pyqtSignal, pyqtSlot
from PyQt6.QtWidgets import QVBoxLayout, QWidget

plt.style.use(["science", "no-latex", "nature", "grid"])


class PlotCanvas(QWidget):
    """
    A PyQt6 widget that contains a Matplotlib figure with interactive anchors.
    Users can interact with the plot to adjust certain parameters. Anchors can be
    dragged and released, and signals are emitted to update underlying values.

    Attributes:
        update_value (pyqtSignal): Signal emitted when anchor positions change.
        figure: Matplotlib Figure instance.
        canvas: FigureCanvas instance for the Figure.
        axes: Matplotlib Axes instance.
        toolbar: NavigationToolbar for the canvas.
        lines (Dict[str, Line2D]): Dictionary of line objects keyed by their name.
        background: Stored background for efficient redrawing.
        dragging_anchor: The currently dragged anchor line object (if any).
        dragging_anchor_group: Which group ('position' or 'height') is being dragged.
        position_anchor_group: An instance of PositionAnchorGroup.
        height_anchor_group: An instance of HeightAnchorGroup.
    """

    update_value = pyqtSignal(list)

    def __init__(self, parent: Optional[QWidget] = None):
        """
        Initialize the plot canvas widget with a toolbar, a figure, and axes.
        Sets up mouse event connections for interactive anchor dragging.
        """
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
        self.dragging_anchor_group = None

        self.canvas.mpl_connect("draw_event", self.on_draw)
        self.canvas.mpl_connect("button_press_event", self.on_click)
        self.canvas.mpl_connect("button_release_event", self.on_release)
        self.canvas.mpl_connect("motion_notify_event", self.on_motion)

        self.mock_plot()

    def on_draw(self, event):
        """
        Handle the draw_event to capture the background after the figure is first drawn.
        This background can be restored later for performance.
        """
        logger.debug("Capturing the canvas background after initial draw.")
        self.background = self.canvas.copy_from_bbox(self.figure.bbox)

    def restore_background(self):
        """Restore the previously saved background to the canvas."""
        self.canvas.restore_region(self.background)

    def mock_plot(self, data=None):
        """
        Create a mock plot for demonstration or initialization.

        Args:
            data: Optional data list. If None, a default sequence is plotted.
        """
        if data is None:
            data = [1, 2, 3, 4, 5]
        logger.debug("Plotting mock data for initial display.")
        self.add_or_update_line("mock", range(len(data)), data)

    def add_or_update_line(self, key, x, y, **kwargs):
        """
        Add a new line or update an existing line on the axes.

        Args:
            key: Unique key name for the line.
            x: x-values for the line data.
            y: y-values for the line data.
            kwargs: Additional Matplotlib line properties.
        """
        if key in self.lines:
            logger.debug(f"Updating line '{key}' with new data.")
            line = self.lines[key]
            line.set_data(x, y)
        else:
            logger.debug(f"Adding a new line '{key}' to the plot.")
            (line,) = self.axes.plot(x, y, **kwargs)
            self.lines[key] = line
        self.canvas.draw_idle()
        self.figure.tight_layout()

    def plot_data_from_dataframe(self, data: pd.DataFrame):
        """
        Plot data from a Pandas DataFrame. The DataFrame is expected to contain
        a 'temperature' column for the x-axis, and one or more other columns
        for the y-values.

        Args:
            data: Pandas DataFrame with columns including 'temperature'.
        """
        self.axes.clear()
        self.lines.clear()

        if "temperature" in data.columns:
            logger.debug("Plotting file data from DataFrame.")
            x = data["temperature"]
            for column in data.columns:
                if column != "temperature":
                    self.add_or_update_line(column, x, data[column], label=column)
        else:
            logger.error("DataFrame does not contain 'temperature' column.")
            console.log("The file does not contain a 'temperature' column for X-axis.")

    def plot_mse_history(self, mse_data):
        if not mse_data:
            return
        times, mses = zip(*mse_data)

        self.axes.clear()
        self.lines.clear()

        self.axes.set_title("MSE over time")
        self.axes.set_xlabel("Time")
        self.axes.set_ylabel("MSE")

        self.add_or_update_line("mse_line", times, mses, color="red", marker="o", linestyle="-")

        self.axes.xaxis.set_major_locator(mdates.AutoDateLocator())
        self.axes.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M:%S"))
        self.figure.autofmt_xdate()

    def determine_line_properties(self, reaction_name):
        """
        Determine line properties (such as linewidth, linestyle, color)
        based on the given reaction name patterns.

        Args:
            reaction_name: A string identifying the reaction line.

        Returns:
            dict: Line properties for Matplotlib.
        """
        if "cumulative_upper_bound" in reaction_name or "cumulative_lower_bound" in reaction_name:
            return {"linewidth": 0.1, "linestyle": "-", "color": "grey"}
        elif "cumulative_coeffs" in reaction_name:
            return {"linewidth": 1, "linestyle": "dotted"}
        elif "upper_bound_coeffs" in reaction_name or "lower_bound_coeffs" in reaction_name:
            return {"linewidth": 1.25, "linestyle": "-."}
        else:
            return {}

    def update_fill_between(self):
        """
        Update the fill_between regions if both upper and lower bound lines are present.
        This adds a shaded area between upper and lower bounds to visually indicate the range.
        """
        if "cumulative_upper_bound_coeffs" in self.lines and "cumulative_lower_bound_coeffs" in self.lines:
            x = self.lines["cumulative_upper_bound_coeffs"].get_xdata()
            upper_y = self.lines["cumulative_upper_bound_coeffs"].get_ydata()
            lower_y = self.lines["cumulative_lower_bound_coeffs"].get_ydata()
            logger.debug("Filling area between cumulative bounds.")
            self.axes.fill_between(x, lower_y, upper_y, color="grey", alpha=0.1)

        if "upper_bound_coeffs" in self.lines and "lower_bound_coeffs" in self.lines:
            x = self.lines["upper_bound_coeffs"].get_xdata()
            upper_y = self.lines["upper_bound_coeffs"].get_ydata()
            lower_y = self.lines["lower_bound_coeffs"].get_ydata()
            logger.debug("Filling area between direct bounds.")
            self.axes.fill_between(x, lower_y, upper_y, color="grey", alpha=0.1)

    @pyqtSlot(tuple, list)
    def plot_reaction(self, keys, values):
        """
        Slot to plot reaction data. If the reaction line already exists, it will be
        removed and re-plotted with new data.

        Args:
            keys: A tuple containing (file_name, reaction_name).
            values: A list containing [x_values, y_values].
        """
        file_name, reaction_name = keys
        x, y = values

        if reaction_name in self.lines:
            logger.debug(f"Removing existing line '{reaction_name}' before replotting.")
            line = self.lines[reaction_name]
            line.remove()
            del self.lines[reaction_name]

        line_properties = self.determine_line_properties(reaction_name)
        logger.debug(f"Plotting reaction '{reaction_name}' with provided data.")
        self.add_or_update_line(reaction_name, x, y, **line_properties)

    @pyqtSlot(dict)
    def add_anchors(self, reaction_data: dict):
        """
        Slot to add anchors to the plot based on given reaction data. This will create
        both position and height anchor groups and plot their initial positions.

        Args:
            reaction_data: A dictionary containing reaction coefficients and bounds.
        """
        logger.debug(f"Received reaction data for anchors: {reaction_data}")

        center_params = reaction_data["coeffs"][2]
        upper_params = reaction_data["upper_bound_coeffs"][2]
        lower_params = reaction_data["lower_bound_coeffs"][2]

        # Create anchor groups
        self.position_anchor_group = PositionAnchorGroup(self.axes, center_params, upper_params, lower_params)
        self.height_anchor_group = HeightAnchorGroup(self.axes, center_params, upper_params, lower_params)

        self.canvas.draw_idle()
        self.figure.tight_layout()

    def find_dragging_anchor(self, event, anchor_group):
        """
        Determine if the mouse click event took place on any of the anchors in the given group.

        Args:
            event: Matplotlib mouse event.
            anchor_group: The anchor group to check.

        Returns:
            The anchor line object if an anchor was clicked, else None.
        """
        if anchor_group.center.contains(event)[0]:
            return anchor_group.center
        elif anchor_group.upper_bound.contains(event)[0] or anchor_group.lower_bound.contains(event)[0]:
            return anchor_group.upper_bound if anchor_group.upper_bound.contains(event)[0] else anchor_group.lower_bound
        return None

    def log_anchor_positions(self, anchor_group):
        """
        Log positions of the provided anchor group for debugging purposes.

        Args:
            anchor_group: An instance of an anchor group.
        """
        anchor_group.log_anchor_positions()

    def update_anchor_position(self, event, anchor_group, axis):
        """
        Update the position of the currently dragged anchor in the specified anchor group.

        Args:
            event: Matplotlib mouse event containing the new coordinates.
            anchor_group: The anchor group to be updated.
            axis: 'x' or 'y' axis along which to update the anchor.
        """
        if self.dragging_anchor == anchor_group.center:
            if axis == "x":
                anchor_group.set_center_position(event.xdata)
            else:
                anchor_group.set_center_position(event.ydata)
        elif self.dragging_anchor in [anchor_group.upper_bound, anchor_group.lower_bound]:
            if axis == "x":
                anchor_group.set_bound_position(self.dragging_anchor, event.xdata)
            else:
                anchor_group.set_bound_position(self.dragging_anchor, event.ydata)

    def on_click(self, event):
        """
        Handle mouse button press events. Check if an anchor was clicked and
        initiate dragging if so.

        Args:
            event: Matplotlib mouse event.
        """
        logger.debug(f"Mouse button pressed at x={event.xdata}, y={event.ydata}")
        if event.inaxes != self.axes:
            return

        self.dragging_anchor = self.find_dragging_anchor(event, self.position_anchor_group)
        if self.dragging_anchor:
            self.dragging_anchor_group = "position"
        else:
            self.dragging_anchor = self.find_dragging_anchor(event, self.height_anchor_group)
            if self.dragging_anchor:
                self.dragging_anchor_group = "height"

    def _calculate_center(self, positions: dict[str, tuple]):
        """
        Calculate the center point between the upper and lower bounds.

        Args:
            positions: Dictionary of 'upper_bound' and 'lower_bound' positions.

        Returns:
            dict: A dictionary with a 'center' key containing the (x, y) of the calculated center.
        """
        center_x = (positions["upper_bound"][0] + positions["lower_bound"][0]) / 2
        center_y = (positions["upper_bound"][1] + positions["lower_bound"][1]) / 2
        return {"center": (center_x, center_y)}

    def on_release(self, event):
        """
        Handle mouse button release events. When an anchor drag finishes, this method
        calculates the updated positions of bounds and center, emits signals, and logs
        the final positions.

        Args:
            event: Matplotlib mouse event.
        """
        logger.debug(f"Mouse button released at x={event.xdata}, y={event.ydata}")

        if self.dragging_anchor_group:
            logger.debug(f"Anchor group being updated: {self.dragging_anchor_group}")

            positions = (
                self.position_anchor_group if self.dragging_anchor_group == "position" else self.height_anchor_group
            ).get_bound_positions()
            logger.debug(f"New anchor positions: {positions}")

            axis = "z" if self.dragging_anchor_group == "position" else "h"

            updates = [
                {
                    "path_keys": ["upper_bound_coeffs", axis],
                    "operation": "update_value",
                    "value": positions["upper_bound"][0 if axis == "z" else 1],
                },
                {
                    "path_keys": ["lower_bound_coeffs", axis],
                    "operation": "update_value",
                    "value": positions["lower_bound"][0 if axis == "z" else 1],
                },
            ]
            center = self._calculate_center(positions)
            updates.append(
                {
                    "path_keys": ["coeffs", axis],
                    "operation": "update_value",
                    "value": center["center"][0 if axis == "z" else 1],
                }
            )
            self.update_value.emit(updates)

        self.dragging_anchor = None
        self.dragging_anchor_group = None

        # Log final anchor positions for both groups
        self.log_anchor_positions(self.position_anchor_group)
        self.log_anchor_positions(self.height_anchor_group)

    def on_motion(self, event):
        """
        Handle mouse motion events. If an anchor is currently being dragged,
        update its position accordingly. This method updates position and height
        anchors on separate axes.

        Args:
            event: Matplotlib mouse event.
        """
        if self.dragging_anchor is None or event.inaxes != self.axes:
            return

        # Update horizontal position anchors
        self.update_anchor_position(event, self.position_anchor_group, "x")

        # Update vertical height anchors
        self.update_anchor_position(event, self.height_anchor_group, "y")

        self.canvas.draw_idle()
        self.figure.tight_layout()
        logger.debug("Redrawing canvas after anchor motion.")
