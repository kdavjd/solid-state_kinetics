from core.logger_config import logger
from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot
from PyQt6.QtWidgets import QSplitter, QVBoxLayout, QWidget

from ..console_widget import ConsoleWidget
from .PlotCanvas.plot_canvas import PlotCanvas
from .sidebar import SideBar
from .sub_sidebar.sub_side_hub import SubSideHub

MIN_WIDTH_SIDEBAR = 220
MIN_WIDTH_SUBSIDEBAR = 220
MIN_WIDTH_CONSOLE = 150
MIN_WIDTH_PLOTCANVAS = 500
SPLITTER_WIDTH = 100
MIN_HEIGHT_MAINTAB = 700
COMPONENTS_MIN_WIDTH = (
    MIN_WIDTH_SIDEBAR + MIN_WIDTH_SUBSIDEBAR + MIN_WIDTH_CONSOLE + MIN_WIDTH_PLOTCANVAS + SPLITTER_WIDTH
)


class MainTab(QWidget):
    active_file_modify_signal = pyqtSignal(dict)
    calculations_data_modify_signal = pyqtSignal(dict)
    processing_signal = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.setMinimumHeight(MIN_HEIGHT_MAINTAB)
        self.setMinimumWidth(COMPONENTS_MIN_WIDTH + SPLITTER_WIDTH)

        self.splitter = QSplitter(Qt.Orientation.Horizontal, self)
        self.layout.addWidget(self.splitter)

        self.sidebar = SideBar(self)
        self.sidebar.setMinimumWidth(MIN_WIDTH_SIDEBAR)
        self.splitter.addWidget(self.sidebar)

        self.sub_sidebar = SubSideHub(self)
        self.sub_sidebar.setMinimumWidth(MIN_WIDTH_SUBSIDEBAR)
        self.sub_sidebar.hide()
        self.splitter.addWidget(self.sub_sidebar)

        self.plot_canvas = PlotCanvas(self)
        self.plot_canvas.setMinimumWidth(MIN_WIDTH_PLOTCANVAS)
        self.splitter.addWidget(self.plot_canvas)

        self.console_widget = ConsoleWidget(self)
        self.console_widget.setMinimumWidth(MIN_WIDTH_CONSOLE)
        self.splitter.addWidget(self.console_widget)

        self.sidebar.sub_side_bar_needed.connect(self.toggle_sub_sidebar)
        self.sidebar.console_show_signal.connect(self.toggle_console_visibility)
        self.sub_sidebar.experiment_sub_bar.action_buttons_block.cancel_changes_clicked.connect(
            self.refer_to_active_file
        )
        self.sub_sidebar.experiment_sub_bar.action_buttons_block.derivative_clicked.connect(self.refer_to_active_file)
        self.sub_sidebar.deconvolution_sub_bar.reactions_table.reaction_added.connect(self.refer_to_calculations_data)
        self.sub_sidebar.deconvolution_sub_bar.reactions_table.reaction_removed.connect(self.refer_to_calculations_data)
        self.sub_sidebar.deconvolution_sub_bar.reactions_table.reaction_chosed.connect(self.refer_to_calculations_data)
        self.sub_sidebar.deconvolution_sub_bar.update_value.connect(self.refer_to_calculations_data)
        self.sidebar.active_file_selected.connect(self.sub_sidebar.deconvolution_sub_bar.reactions_table.switch_file)
        self.plot_canvas.update_value.connect(self.update_anchors_slot)
        self.sub_sidebar.deconvolution_sub_bar.calc_buttons.calculation_started.connect(self.refer_to_calculations_data)

    def initialize_sizes(self):
        total_width = self.width()

        sidebar_ratio = MIN_WIDTH_SIDEBAR / COMPONENTS_MIN_WIDTH
        subsidebar_ratio = MIN_WIDTH_SUBSIDEBAR / COMPONENTS_MIN_WIDTH
        console_ratio = MIN_WIDTH_CONSOLE / COMPONENTS_MIN_WIDTH

        sidebar_width = int(total_width * sidebar_ratio)
        console_width = int(total_width * console_ratio) if self.console_widget.isVisible() else 0
        sub_sidebar_width = int(total_width * subsidebar_ratio) if self.sub_sidebar.isVisible() else 0
        canvas_width = total_width - (sidebar_width + sub_sidebar_width + console_width)
        self.splitter.setSizes([sidebar_width, sub_sidebar_width, canvas_width, console_width])

    def showEvent(self, event):
        super().showEvent(event)
        self.initialize_sizes()

    def toggle_sub_sidebar(self, content_type):
        if content_type:
            if content_type in self.sidebar.get_experiment_files_names():
                self.sub_sidebar.update_content("Эксперимент")
            else:
                self.sub_sidebar.update_content(content_type)
            self.sub_sidebar.setVisible(True)
        else:
            self.sub_sidebar.setVisible(False)
        self.initialize_sizes()

    def toggle_console_visibility(self, visible):
        self.console_widget.setVisible(visible)
        self.initialize_sizes()

    def refer_to_calculations_data(self, params: dict):
        active_file_name = self.sidebar.active_file_item.text() if self.sidebar.active_file_item else "no_file"
        params["path_keys"].insert(0, active_file_name)
        logger.debug(f"Данные: {params} запрашивают операцию изменения данных расчета")
        self.calculations_data_modify_signal.emit(params)

    def refer_to_active_file(self, params: dict):
        params["file_name"] = self.sidebar.active_file_item.text() if self.sidebar.active_file_item else "no_file"
        logger.debug(f"Активный файл: {params['file_name']} запрашивает операцию: {params['operation']}")
        self.active_file_modify_signal.emit(params)

    @pyqtSlot(list)
    def update_anchors_slot(self, params_list: list):
        self.processing_signal.emit(True)
        for i, params in enumerate(params_list):
            params["path_keys"].insert(
                0,
                self.sub_sidebar.deconvolution_sub_bar.reactions_table.active_reaction,
            )
            if i == len(params_list) - 1:
                self.processing_signal.emit(False)
            self.refer_to_calculations_data(params)
