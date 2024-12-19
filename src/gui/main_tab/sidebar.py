from os import path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QStandardItem, QStandardItemModel
from PyQt6.QtWidgets import QDialog, QMessageBox, QTreeView, QVBoxLayout, QWidget

from src.core.logger_config import logger
from src.gui.main_tab.load_file_button import LoadButton
from src.gui.main_tab.sub_sidebar.model_based.model_based import SelectFileDataDialog


class SideBar(QWidget):
    """
    A sidebar widget that provides a tree view for navigating through project data,
    experiments, and settings. It includes actions for adding, deleting, and selecting files
    for experiments, as well as controlling the display of a console.
    """

    file_selected = pyqtSignal(tuple)
    sub_side_bar_needed = pyqtSignal(str)
    chosen_experiment_signal = pyqtSignal(str)
    console_show_signal = pyqtSignal(bool)
    active_file_selected = pyqtSignal(str)
    to_main_window_signal = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout()

        self.tree_view = QTreeView()
        self.tree_view.clicked.connect(self.on_item_clicked)
        self.model = QStandardItemModel()
        self.model.setHorizontalHeaderLabels(["Project Management"])
        self.tree_view.setModel(self.model)

        # Initialize experiment data section
        self.experiments_data_root = QStandardItem("experiments")
        self.add_data_item = QStandardItem("add file data")
        self.delete_data_item = QStandardItem("delete selected")
        self.experiments_data_root.appendRow(self.add_data_item)
        self.experiments_data_root.appendRow(self.delete_data_item)
        self.model.appendRow(self.experiments_data_root)

        # Initialize model-free calculation section
        self.model_free_root = QStandardItem("model-free calculation")
        self.model.appendRow(self.model_free_root)
        self.model_free_root.appendRow(QStandardItem("deconvolution"))
        self.model_free_root.appendRow(QStandardItem("Ea"))
        self.model_free_root.appendRow(QStandardItem("A"))

        # Initialize model-based calculation section
        self.model_based_root = QStandardItem("model-based calculation")
        self.model.appendRow(self.model_based_root)
        self.add_new_series_item = QStandardItem("add new series")
        self.import_series_item = QStandardItem("import series")
        self.delete_series_item = QStandardItem("delete series")
        self.model_based_root.appendRow(self.add_new_series_item)
        self.model_based_root.appendRow(self.import_series_item)
        self.model_based_root.appendRow(self.delete_series_item)

        # Initialize settings section
        self.settings_root = QStandardItem("settings")
        self.console_subroot = QStandardItem("console")
        self.console_show_state = QStandardItem("show")
        self.console_show_state.setCheckable(True)
        self.console_show_state.setCheckState(Qt.CheckState.Checked)
        self.console_hide_state = QStandardItem("hide")
        self.console_hide_state.setCheckable(True)
        self.model.appendRow(self.settings_root)
        self.settings_root.appendRow(self.console_subroot)
        self.console_subroot.appendRow(self.console_show_state)
        self.console_subroot.appendRow(self.console_hide_state)

        self.layout.addWidget(self.tree_view)
        self.setLayout(self.layout)

        # Load button setup
        self.load_button = LoadButton(self)
        self.load_button.file_selected.connect(self.add_experiment_file)

        self.active_file_item = None

    def mark_as_active(self, item):
        """
        Marks the provided item as active by making its font bold.

        Args:
            item: The item to mark as active.
        """
        if self.active_file_item:
            self.unmark_active_state(self.active_file_item)
        self.mark_active_state(item)
        self.active_file_item = item
        self.active_file_selected.emit(item.text())
        logger.debug(f"Active file: {item.text()}")

    def mark_active_state(self, item):
        """
        Applies bold font style to the given item to indicate it's active.

        Args:
            item: The item to apply bold font to.
        """
        font = item.font()
        font.setBold(True)
        item.setFont(font)

    def unmark_active_state(self, item):
        """
        Removes bold font style from the given item to indicate it's not active anymore.

        Args:
            item: The item to remove bold font from.
        """
        font = item.font()
        font.setBold(False)
        item.setFont(font)

    def on_item_clicked(self, index):  # noqa: C901
        """
        Handles the item click event in the tree view. Performs different actions
        based on which item is clicked.

        Args:
            index: The index of the clicked item.
        """
        item = self.model.itemFromIndex(index)
        if item == self.add_data_item:
            self.load_button.open_file_dialog()
        elif item == self.delete_data_item:
            self.delete_active_file()
        elif item == self.add_new_series_item:
            self.add_new_series()
        elif item == self.import_series_item:
            self.import_series()
        elif item == self.delete_series_item:
            self.delete_series()
        elif item.parent() == self.experiments_data_root:
            self.sub_side_bar_needed.emit(item.text())
            self.chosen_experiment_signal.emit(item.text())
            self.mark_as_active(item)
        elif item == self.console_show_state:
            if item.checkState() == Qt.CheckState.Checked:
                self.console_show_signal.emit(True)
                self.console_hide_state.setCheckState(Qt.CheckState.Unchecked)
        elif item == self.console_hide_state:
            if item.checkState() == Qt.CheckState.Checked:
                self.console_show_signal.emit(False)
                self.console_show_state.setCheckState(Qt.CheckState.Unchecked)
        elif item.parent() == self.model_free_root:
            self.sub_side_bar_needed.emit(item.text())
        elif item.parent() == self.model_based_root:
            self.sub_side_bar_needed.emit(item.text())
        else:
            self.sub_side_bar_needed.emit("")

    def add_new_series(self):
        """
        Handles the 'add new series' action:
        - Sends a request to get all data keys.
        """
        logger.debug("Add New Series clicked.")
        request = {"operation": "add_new_series"}
        self.to_main_window_signal.emit(request)

    def open_select_files_dialog(self, df_copies):
        """
        Opens a dialog to allow the user to select files for the new series.

        Args:
            df_copies (dict): A dictionary of file names to their corresponding dataframes.
        """
        dialog = SelectFileDataDialog(df_copies, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            selected_files = dialog.get_selected_files()
            if selected_files:
                logger.debug(f"Selected files for series: {selected_files}")
                return selected_files
            else:
                logger.info("No files selected for series.")

    def import_series(self):
        """
        Handles the 'import series' action.
        This method should be implemented based on specific requirements.
        """
        QMessageBox.information(self, "Import Series", "Import Series functionality is not yet implemented.")
        logger.debug("Import Series clicked. Functionality not implemented.")

    def delete_series(self):
        """
        Handles the 'delete series' action:
        - Deletes the selected series from the tree view.
        - Logs the deletion.
        """
        index = self.tree_view.currentIndex()
        item = self.model.itemFromIndex(index)

        if item and item.parent() == self.model_based_root:
            series_name = item.text()
            reply = QMessageBox.question(
                self,
                "Delete Series",
                f"Are you sure you want to delete the series '{series_name}'?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.model_based_root.removeRow(item.row())
                logger.info(f"Series deleted: {series_name}")
        else:
            QMessageBox.warning(
                self,
                "Deletion Error",
                "Please select a valid series to delete.",
            )
            logger.warning("Delete Series clicked, but no valid series was selected.")

    def add_experiment_file(self, file_info):
        """
        Adds a new experiment file to the sidebar and makes it the active file.

        Args:
            file_info: A tuple containing the file path and other relevant info.
        """
        new_file_item = QStandardItem(path.basename(file_info[0]))
        self.experiments_data_root.insertRow(self.experiments_data_root.rowCount() - 2, new_file_item)
        self.tree_view.expandAll()
        self.mark_as_active(new_file_item)
        self.sub_side_bar_needed.emit(new_file_item.text())
        logger.debug(f"New file added and set as active: {new_file_item.text()}")
        self.reposition_experiments_data_items()

    def delete_active_file(self):
        """
        Deletes the currently active file from the tree view.
        If no file is selected, a warning message is shown.
        """
        if not self.active_file_item:
            QMessageBox.warning(self, "Error", "Please select a file to delete.")
            return

        parent = self.active_file_item.parent()
        if parent:
            file_name = self.active_file_item.text()
            parent.removeRow(self.active_file_item.row())
            logger.debug(f"File deleted: {file_name}")
            self.active_file_item = None
            self.reposition_experiments_data_items()
        else:
            QMessageBox.critical(self, "Error", "Failed to delete the selected file.")

    def reposition_experiments_data_items(self):
        """
        Repositions the 'Add New Data' and 'Delete Selected Data' items to the end of the `experiments_data_root` node.
        This ensures that they are always at the bottom of the experiment data section.
        """
        self.experiments_data_root.removeRow(self.add_data_item.row())
        self.experiments_data_root.removeRow(self.delete_data_item.row())

        self.add_data_item = QStandardItem("add file data")
        self.delete_data_item = QStandardItem("delete selected")

        self.experiments_data_root.appendRow(self.add_data_item)
        self.experiments_data_root.appendRow(self.delete_data_item)

    def get_experiment_files_names(self) -> list[str]:
        """
        Returns a list of names of all experiment files currently listed in the sidebar.

        Returns:
            A list of strings representing the names of experiment files.
        """
        files_names = []
        for row in range(self.experiments_data_root.rowCount() - 1):
            item = self.experiments_data_root.child(row)
            if item is not None:
                files_names.append(item.text())
        return files_names
