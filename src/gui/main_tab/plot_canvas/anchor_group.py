from core.logger_config import logger


class AnchorGroup:
    def __init__(self, axes, center_params, upper_params, lower_params):
        self.axes = axes
        h_center, z_center, _ = center_params[:3]
        h_upper, z_upper, _ = upper_params[:3]
        h_lower, z_lower, _ = lower_params[:3]

        (self.center,) = self.axes.plot(z_center, h_center, "ko", picker=5)
        (self.upper_bound,) = self.axes.plot(z_upper, h_upper, "ro", picker=5)
        (self.lower_bound,) = self.axes.plot(z_lower, h_lower, "ro", picker=5)

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

    def get_bound_positions(self):
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
    def __init__(self, axes, center_params, upper_params, lower_params):
        _, z_center, _ = center_params[:3]
        _, z_upper, _ = upper_params[:3]
        _, z_lower, _ = lower_params[:3]

        # Переопределяем y значения для PositionAnchorGroup
        super().__init__(axes, (0, z_center, 0), (0, z_upper, 0), (0, z_lower, 0))

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
