"""This module provides classes and functionalities for plotting data with interactive anchors
to adjust certain parameters (like height and position) on a matplotlib plot canvas integrated
into a PyQt6 GUI. It includes three main anchor group classes:

- AnchorGroup: Base class for handling a trio of anchors (center, upper bound, lower bound).
- PositionAnchorGroup: Specialized for handling horizontal position adjustments.
- HeightAnchorGroup: Specialized for handling vertical height adjustments.

Additionally, it provides the PlotCanvas class which integrates a Matplotlib figure, toolbar,
and the anchor groups into a PyQt6 widget, allowing interactive data visualization and editing.
"""

import matplotlib.pyplot as plt
import scienceplots  # noqa pylint: disable=unused-import
from core.logger_config import logger

plt.style.use(["science", "no-latex", "nature", "grid"])


class AnchorGroup:
    """
    A base class for managing a group of three anchors: a center anchor,
    an upper bound anchor, and a lower bound anchor. Anchors are represented
    as points on a Matplotlib axes object. This class provides methods to
    reposition anchors and maintain symmetry between upper and lower bounds
    relative to the center.

    Attributes:
        axes: The Matplotlib axes on which the anchors are plotted.
        center: The center anchor line object.
        upper_bound: The upper bound anchor line object.
        lower_bound: The lower bound anchor line object.
    """

    def __init__(self, axes, center_params, upper_params, lower_params):
        """
        Initialize the AnchorGroup with given anchor parameters.

        Args:
            axes: Matplotlib axes to plot the anchors.
            center_params: A tuple or list containing center anchor parameters
                           in order (h_center, z_center, additional_data).
            upper_params: A tuple or list containing upper anchor parameters
                          in order (h_upper, z_upper, additional_data).
            lower_params: A tuple or list containing lower anchor parameters
                          in order (h_lower, z_lower, additional_data).
        """
        self.axes = axes
        h_center, z_center, _ = center_params[:3]
        h_upper, z_upper, _ = upper_params[:3]
        h_lower, z_lower, _ = lower_params[:3]

        (self.center,) = self.axes.plot(z_center, h_center, "ko", picker=5)
        (self.upper_bound,) = self.axes.plot(z_upper, h_upper, "ro", picker=5)
        (self.lower_bound,) = self.axes.plot(z_lower, h_lower, "ro", picker=5)

    def set_center_position(self, x, y):
        """
        Move the center anchor to a new (x, y) position and shift both upper and lower
        anchors accordingly to maintain their relative offsets.

        Args:
            x: New x-coordinate for the center anchor.
            y: New y-coordinate for the center anchor.
        """
        dx = x - self.center.get_xdata()[0]
        dy = y - self.center.get_ydata()[0]

        self.center.set_xdata(x)
        self.center.set_ydata(y)

        self.upper_bound.set_xdata(self.upper_bound.get_xdata()[0] + dx)
        self.upper_bound.set_ydata(self.upper_bound.get_ydata()[0] + dy)
        self.lower_bound.set_xdata(self.lower_bound.get_xdata()[0] + dx)
        self.lower_bound.set_ydata(self.lower_bound.get_ydata()[0] + dy)

    def set_bound_position(self, bound, x, y):
        """
        Move an upper or lower bound anchor to a new (x, y) position with constraints:
        - The upper bound cannot go below the center anchor.
        - The lower bound cannot go above the center anchor.

        Args:
            bound: Either self.upper_bound or self.lower_bound.
            x: New x-coordinate for the given bound anchor.
            y: New y-coordinate for the given bound anchor.
        """
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
        """Log current positions of all three anchors for debugging."""
        logger.debug(f"Center anchor position: x={self.center.get_xdata()[0]}, y={self.center.get_ydata()[0]}")
        logger.debug(
            f"Upper bound anchor position: x={self.upper_bound.get_xdata()[0]}, y={self.upper_bound.get_ydata()[0]}"
        )
        logger.debug(
            f"Lower bound anchor position: x={self.lower_bound.get_xdata()[0]}, y={self.lower_bound.get_ydata()[0]}"
        )

    def get_bound_positions(self):
        """
        Get current positions of the upper and lower bound anchors.

        Returns:
            dict: A dictionary with 'upper_bound' and 'lower_bound' keys and
                  corresponding (x, y) tuples.
        """
        return {
            "upper_bound": (
                self.upper_bound.get_xdata()[0],
                self.upper_bound.get_ydata()[0],
            ),
            "lower_bound": (
                self.lower_bound.get_xdata()[0],
                self.lower_bound.get_ydata()[0],
            ),
        }


class PositionAnchorGroup(AnchorGroup):
    """
    A specialized AnchorGroup for managing horizontal (position) adjustments.
    Here, all anchors share the same y-value (fixed at 0). This class overrides
    methods to move anchors only along the x-axis and maintains symmetrical
    bounds around the center.
    """

    def __init__(self, axes, center_params, upper_params, lower_params):
        """
        Initialize the PositionAnchorGroup. The original parameters for center,
        upper, and lower anchors are transformed so that their y-values are fixed
        at zero. Only x-values represent the positioning along the horizontal axis.

        Args:
            axes: Matplotlib axes to plot the anchors.
            center_params: Parameters for the center anchor.
            upper_params: Parameters for the upper anchor.
            lower_params: Parameters for the lower anchor.
        """
        _, z_center, _ = center_params[:3]
        _, z_upper, _ = upper_params[:3]
        _, z_lower, _ = lower_params[:3]
        super().__init__(axes, (0, z_center, 0), (0, z_upper, 0), (0, z_lower, 0))

    def set_center_position(self, x):
        """
        Set the center anchor position along the x-axis. This also adjusts the
        upper and lower anchors horizontally to maintain relative distances.

        Args:
            x: New x-coordinate for the center anchor.
        """
        dx = x - self.center.get_xdata()[0]

        self.center.set_xdata(x)
        self.center.set_ydata(0)

        self.upper_bound.set_xdata(self.upper_bound.get_xdata()[0] + dx)
        self.upper_bound.set_ydata(0)
        self.lower_bound.set_xdata(self.lower_bound.get_xdata()[0] + dx)
        self.lower_bound.set_ydata(0)

    def set_bound_position(self, bound, x):
        """
        Set the position of a bound anchor along the x-axis, ensuring the upper
        bound stays to the right of the center and the lower bound stays to the left.

        Args:
            bound: Either self.upper_bound or self.lower_bound.
            x: New x-coordinate for the given bound anchor.
        """
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
    """
    A specialized AnchorGroup for managing vertical (height) adjustments.
    This class allows moving anchors only along the y-axis while keeping
    their x-coordinates constant.
    """

    def __init__(self, axes, center_params, upper_params, lower_params):
        """
        Initialize the HeightAnchorGroup with the given parameters. The parent
        class manages the creation of anchors. This class focuses on vertical adjustments.

        Args:
            axes: Matplotlib axes to plot the anchors.
            center_params: Parameters for the center anchor.
            upper_params: Parameters for the upper anchor.
            lower_params: Parameters for the lower anchor.
        """
        super().__init__(axes, center_params, upper_params, lower_params)

    def set_center_position(self, y):
        """
        Set the center anchor's vertical position. The horizontal position remains unchanged.

        Args:
            y: New y-coordinate for the center anchor.
        """
        super().set_center_position(self.center.get_xdata()[0], y)

    def set_bound_position(self, bound, y):
        """
        Adjust the vertical position of an upper or lower bound anchor. The horizontal
        position remains unchanged. The upper bound cannot be below the center, and
        the lower bound cannot be above the center.

        Args:
            bound: Either self.upper_bound or self.lower_bound.
            y: New y-coordinate for the given bound anchor.
        """
        if bound == self.upper_bound and y <= self.center.get_ydata()[0]:
            y = self.center.get_ydata()[0] + 0.1
        elif bound == self.lower_bound and y >= self.center.get_ydata()[0]:
            y = self.center.get_ydata()[0] - 0.1

        bound.set_ydata(y)

        # Update opposite bound symmetrically relative to the center
        if bound == self.upper_bound:
            opposite_bound = self.lower_bound
            dy = y - self.center.get_ydata()[0]
            opposite_bound.set_ydata(self.center.get_ydata()[0] - dy)
        else:
            opposite_bound = self.upper_bound
            dy = self.center.get_ydata()[0] - y
            opposite_bound.set_ydata(self.center.get_ydata()[0] + dy)
