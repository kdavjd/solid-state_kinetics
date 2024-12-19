from functools import reduce

import pandas as pd
from core.base_signals import BaseSignals, BaseSlots
from PyQt6.QtCore import pyqtSignal, pyqtSlot
from PyQt6.QtWidgets import QMainWindow, QTabWidget

from src.core.logger_config import logger
from src.core.logger_console import LoggerConsole as console
from src.gui.main_tab.main_tab import MainTab
from src.gui.table_tab.table_tab import TableTab


class MainWindow(QMainWindow):
    to_main_tab_signal = pyqtSignal(dict)

    def __init__(self, signals: BaseSignals):
        super().__init__()
        self.setWindowTitle("Solid state kinetics")

        self.tabs = QTabWidget(self)
        self.setCentralWidget(self.tabs)

        self.main_tab = MainTab(self)
        self.table_tab = TableTab(self)

        self.tabs.addTab(self.main_tab, "Main")
        self.tabs.addTab(self.table_tab, "Table")

        self.signals = signals
        self.actor_name = "main_window"

        self.basic_signals = BaseSlots(actor_name=self.actor_name, signals=self.signals)

        self.signals.register_component(self.actor_name, self.process_request, self.process_response)

        self.main_tab.to_main_window_signal.connect(self.handle_request_from_main_tab)
        self.main_tab.sidebar.to_main_window_signal.connect(self.handle_request_from_main_tab)
        self.to_main_tab_signal.connect(self.main_tab.response_slot)

        logger.debug(f"{self.actor_name} init signals and slots.")

    @pyqtSlot(dict)
    def process_request(self, params: dict):
        operation = params.get("operation")
        actor = params.get("actor")
        response = params.copy()
        logger.debug(f"{self.actor_name} handle request '{operation}' from '{actor}'")
        if operation == "get_file_name":
            response["data"] = self.main_tab.sidebar.active_file_item.text()
        if operation == "plot_df":
            df = params.get("df", None)
            self.main_tab.plot_canvas.plot_file_data_from_dataframe(df) if df is not None else logger.error(
                f"{self.actor_name} no df"
            )
            response["data"] = df is not None

        if operation == "plot_mse_line":
            mse_data = params.get("mse_data", [])
            self.main_tab.plot_canvas.plot_mse_history(mse_data)
            response["data"] = True

        if operation == "calculation_finished":
            self.main_tab.sub_sidebar.deconvolution_sub_bar.calc_buttons.revert_to_default()
            response["data"] = True

        else:
            logger.warning(f"{self.actor_name} received unknown operation '{operation}'")
        response["target"], response["actor"] = response["actor"], response["target"]
        self.signals.response_signal.emit(response)

    @pyqtSlot(dict)
    def process_response(self, params: dict):
        logger.debug(f"{self.actor_name} received response: {params}")
        self.basic_signals.process_response(params)

    def handle_request_cycle(self, target: str, operation: str, **kwargs):
        result = self.basic_signals.handle_request_cycle(target, operation, **kwargs)
        logger.debug(f"handle_request_cycle result for '{operation}': {result}")
        return result

    @pyqtSlot(dict)
    def handle_request_from_main_tab(self, params: dict):  # noqa: C901
        operation = params.pop("operation")

        logger.debug(f"{self.actor_name} handle_request_from_main_tab '{operation}")

        if operation == "differential":
            params["function"] = self.handle_request_cycle("active_file_operations", operation)
            is_modifyed = self.handle_request_cycle("file_data", operation, **params)
            if is_modifyed:
                df = self.handle_request_cycle("file_data", "get_df_data", **params)
                self.main_tab.plot_canvas.plot_file_data_from_dataframe(df)
            else:
                logger.error(f"{self.actor_name} no response in handle_request_from_main_tab")

        if operation == "add_reaction":
            is_ok = self.handle_request_cycle("calculations_data_operations", operation, **params)
            if not is_ok:
                console.log(
                    "\n\nit is necessary to bring the data to da/dT.\
                        \nexperiments -> your experiment -> da/dT"
                )
                self.main_tab.sub_sidebar.deconvolution_sub_bar.reactions_table.on_fail_add_reaction()
                return

        if operation == "highlight_reaction":
            df = self.handle_request_cycle("file_data", "get_df_data", **params)
            self.main_tab.plot_canvas.plot_file_data_from_dataframe(df)
            is_ok = self.handle_request_cycle("calculations_data_operations", operation, **params)
            logger.debug(f"{operation=} {is_ok=}")

        if operation == "remove_reaction":
            is_ok = self.handle_request_cycle("calculations_data_operations", operation, **params)
            logger.debug(f"{operation=} {is_ok=}")

        if operation == "update_value":
            is_ok = self.handle_request_cycle("calculations_data_operations", operation, **params)
            logger.debug(f"{operation=} {is_ok=}")

        if operation == "reset":
            is_ok = self.handle_request_cycle("file_data", operation, **params)
            df = self.handle_request_cycle("file_data", "get_df_data", **params)
            self.main_tab.plot_canvas.plot_file_data_from_dataframe(df)
            logger.debug(f"{operation=} {is_ok=}")

        if operation == "import_reactions":
            data = self.handle_request_cycle("calculations_data", operation, **params)
            self.main_tab.update_reactions_table(data)

        if operation == "export_reactions":
            data = self.handle_request_cycle("calculations_data", "get_value", **params)
            suggested_file_name = params["function"](params["file_name"], data)
            self.main_tab.sub_sidebar.deconvolution_sub_bar.file_transfer_buttons.export_reactions(
                data, suggested_file_name
            )

        if operation == "deconvolution":
            data = self.handle_request_cycle("calculations_data_operations", operation, **params)
            logger.debug(f"{data=}")

        if operation == "stop_calculation":
            _ = self.handle_request_cycle("calculations", "stop_calculation")

        if operation == "add_new_series":
            df_copies = self.handle_request_cycle("file_data", "get_all_data", file_name="all_files")
            selected_files = self.main_tab.sidebar.open_select_files_dialog(df_copies)
            if not selected_files:
                logger.warning(f"{self.actor_name} no files selected for adding new series.")
                return
            merged_df = reduce(
                lambda left, right: pd.merge(left, right, on="temperature", how="outer"), df_copies.values()
            )
            merged_df.sort_values(by="temperature", inplace=True)
            merged_df.interpolate(method="linear", inplace=True)
            logger.info(f"{merged_df=}")

        else:
            logger.error(f"{self.actor_name} unknown operation: {operation},\n\n {params=}")
