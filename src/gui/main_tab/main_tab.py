from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot
from PyQt6.QtWidgets import QSplitter, QVBoxLayout, QWidget

from src.core.app_settings import OperationType
from src.core.logger_config import logger
from src.gui.console_widget import ConsoleWidget
from src.gui.main_tab.plot_canvas.plot_canvas import PlotCanvas
from src.gui.main_tab.sidebar import SideBar
from src.gui.main_tab.sub_sidebar.sub_side_hub import SubSideHub

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
    to_main_window_signal = pyqtSignal(dict)

    def __init__(self, parent=None):
        QWidget.__init__(self, parent)

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
        self.sub_sidebar.experiment_sub_bar.action_buttons_block.cancel_changes_clicked.connect(self.to_main_window)
        self.sub_sidebar.experiment_sub_bar.action_buttons_block.derivative_clicked.connect(self.to_main_window)
        self.sub_sidebar.experiment_sub_bar.action_buttons_block.deconvolution_clicked.connect(self.toggle_sub_sidebar)
        self.sub_sidebar.deconvolution_sub_bar.reactions_table.reaction_added.connect(self.to_main_window)
        self.sub_sidebar.deconvolution_sub_bar.reactions_table.reaction_removed.connect(self.to_main_window)
        self.sub_sidebar.deconvolution_sub_bar.reactions_table.reaction_chosed.connect(self.to_main_window)
        self.sub_sidebar.deconvolution_sub_bar.update_value.connect(self.to_main_window)
        self.sidebar.active_file_selected.connect(self.sub_sidebar.deconvolution_sub_bar.reactions_table.switch_file)
        self.sidebar.active_file_selected.connect(self.select_series)
        self.plot_canvas.update_value.connect(self.update_anchors_slot)
        self.sub_sidebar.deconvolution_sub_bar.calc_buttons.calculation_started.connect(self.to_main_window)
        self.sub_sidebar.ea_sub_bar.create_series_signal.connect(self.to_main_window)
        self.sub_sidebar.deconvolution_sub_bar.file_transfer_buttons.import_reactions_signal.connect(
            self.to_main_window
        )
        self.sub_sidebar.deconvolution_sub_bar.file_transfer_buttons.export_reactions_signal.connect(
            self.to_main_window
        )
        self.sub_sidebar.deconvolution_sub_bar.calc_buttons.calculation_stopped.connect(self.to_main_window)
        self.sub_sidebar.model_based.models_scene.scheme_change_signal.connect(self.to_main_window)
        self.sub_sidebar.model_based.calc_buttons.simulation_started.connect(self.to_main_window)
        self.sub_sidebar.model_based.calc_buttons.simulation_stopped.connect(self.to_main_window)
        self.sub_sidebar.model_based.model_params_changed.connect(self.to_main_window)

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
            if content_type in self.sidebar.get_series_names():
                self.sub_sidebar.update_content("model_based")
            elif content_type in self.sidebar.get_experiment_files_names():
                self.sub_sidebar.update_content("experiments")
            elif content_type == "deconvolution":
                self.sub_sidebar.update_content("deconvolution")
            else:
                self.sub_sidebar.update_content(content_type)
            self.sub_sidebar.setVisible(True)
        else:
            self.sub_sidebar.setVisible(False)
        self.initialize_sizes()

    def toggle_console_visibility(self, visible):
        self.console_widget.setVisible(visible)
        self.initialize_sizes()

    def select_series(self, series_name):
        if series_name in self.sidebar.get_series_names():
            self.to_main_window_signal.emit({"operation": OperationType.SELECT_SERIES, "series_name": series_name})

    @pyqtSlot(dict)
    def to_main_window(self, params: dict):
        file_name = self.sidebar.active_file_item.text() if self.sidebar.active_file_item else "no_file"
        series_name = self.sidebar.active_series_item.text() if self.sidebar.active_series_item else "no_series"
        params["file_name"] = file_name
        params["series_name"] = series_name
        params.setdefault("path_keys", []).insert(0, file_name)
        self.to_main_window_signal.emit(params)

    @pyqtSlot(list)
    def update_anchors_slot(self, params_list: list):
        for i, params in enumerate(params_list):
            params["path_keys"].insert(
                0,
                self.sub_sidebar.deconvolution_sub_bar.reactions_table.active_reaction,
            )
            params["is_chain"] = True
            self.to_main_window(params)
        params["operation"] = OperationType.HIGHLIGHT_REACTION
        self.to_main_window(params)

    def update_reactions_table(self, data: dict):
        active_file_name = self.sidebar.active_file_item.text() if self.sidebar.active_file_item else None
        if not active_file_name:
            logger.error("There is no active file to update the UI.")
            return

        reaction_table = self.sub_sidebar.deconvolution_sub_bar.reactions_table
        reaction_table.switch_file(active_file_name)
        table = reaction_table.reactions_tables[active_file_name]
        table.setRowCount(0)
        reaction_table.reactions_counters[active_file_name] = 0

        for reaction_name, reaction_info in data.items():
            function_name = reaction_info.get("function", "gauss")
            reaction_table.add_reaction(reaction_name=reaction_name, function_name=function_name, emit_signal=False)
        logger.debug("The UI has been successfully updated with loaded reactions.")

    def response_slot(self, params: dict):
        logger.debug(f"response_slot handle {params}")
