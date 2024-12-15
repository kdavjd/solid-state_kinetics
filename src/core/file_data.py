import os
from functools import wraps
from io import StringIO

import chardet
import pandas as pd
from core.base_signals import BaseSlots
from PyQt6.QtCore import pyqtSignal, pyqtSlot

from src.core.logger_config import logger
from src.core.logger_console import LoggerConsole as console


def detect_encoding(func):
    """
    Decorator that detects the file encoding of the file_path attribute
    of the FileData instance before calling the decorated function.

    Parameters
    ----------
    func : callable
        The function to wrap.

    Returns
    -------
    callable
        The wrapped function with `encoding` parameter injected.
    """

    @wraps(func)
    def wrapper(self, *args, **kwargs):
        # Attempt to detect encoding using chardet by reading a portion of the file.
        with open(self.file_path, "rb") as f:
            result = chardet.detect(f.read(100_000))
        kwargs["encoding"] = result["encoding"]
        return func(self, *args, **kwargs)

    return wrapper


def detect_decimal(func):
    """
    Decorator that determines the decimal separator of the data file by
    sampling a subset of lines and comparing comma vs. period occurrence.

    Parameters
    ----------
    func : callable
        The function to wrap.

    Returns
    -------
    callable
        The wrapped function with `decimal` parameter injected.
    """

    @wraps(func)
    def wrapper(self, **kwargs):
        # Determine the encoding to read a sample of the file.
        encoding = kwargs.get("encoding", "utf-8")
        with open(self.file_path, "r", encoding=encoding) as f:
            # Read a sample of lines (up to 100) from the file
            # This is a heuristic to guess the decimal separator.
            sample_lines = [next(f) for _ in range(100)]
        sample_text = "".join(sample_lines)

        # Heuristic: if commas appear more often than periods, assume comma decimal.
        decimal_sep = "," if sample_text.count(",") > sample_text.count(".") else "."
        kwargs["decimal"] = decimal_sep
        return func(self, **kwargs)

    return wrapper


class FileData(BaseSlots):
    """
    The FileData class provides methods to load, store, and manipulate
    data from CSV and TXT files.

    Attributes
    ----------
    data : pandas.DataFrame or None
        The currently loaded DataFrame.
    original_data : dict of {str: pandas.DataFrame}
        A dictionary to store the original loaded dataframes keyed by filename.
    dataframe_copies : dict of {str: pandas.DataFrame}
        Copies of the dataframes for modification without altering originals.
    file_path : str or None
        The path to the currently loaded file.
    delimiter : str
        The delimiter used in the input data file.
    skip_rows : int
        Number of rows to skip from the top of the file.
    columns_names : list[str] or None
        List of column names if provided, otherwise None.
    operations_history : dict
        History of modifications performed on data, keyed by filename.
    loaded_files : set
        Set of file paths that have been successfully loaded to prevent duplicates.
    """

    data_loaded_signal = pyqtSignal(pd.DataFrame)

    def __init__(self, signals):
        super().__init__(actor_name="file_data", signals=signals)
        self.data = None
        self.original_data = {}
        self.dataframe_copies = {}
        self.file_path = None
        self.delimiter = ","
        self.skip_rows = 0
        self.columns_names = None
        self.operations_history = {}
        self.loaded_files = set()

    def log_operation(self, params: dict):
        """
        Log an operation performed on the dataset for a specific file.

        Parameters
        ----------
        params : dict
            Dictionary containing details of the operation. Must contain 'file_name'
            and 'operation' keys.
        """
        file_name = params.pop("file_name")
        if file_name not in self.operations_history:
            self.operations_history[file_name] = []
        self.operations_history[file_name].append({"params": params})
        logger.debug(f"Updated operations history: {self.operations_history}")

    def check_operation_executed(self, file_name: str, operation: str) -> bool:
        if file_name in self.operations_history:
            for operation_record in self.operations_history[file_name]:
                if operation_record["params"]["operation"] == operation:
                    return True
        return False

    @pyqtSlot(tuple)
    def load_file(self, file_info):
        """
        Load a file given its parameters. The file_info tuple is expected
        to contain (file_path, delimiter, skip_rows, columns_names).

        This method checks if the file is already loaded, sets class
        attributes, and decides whether to load a CSV or TXT file.

        Parameters
        ----------
        file_info : tuple
            (file_path, delimiter, skip_rows, columns_names)
        """
        self.file_path, self.delimiter, self.skip_rows, columns_names = file_info

        if self.file_path in self.loaded_files:
            console.log(f"\n\nThe file '{self.file_path}' is already loaded.")
            return

        # If user provided column names as a string, split them appropriately.
        if columns_names:
            column_delimiter = "," if "," in columns_names else " "
            self.columns_names = [name.strip() for name in columns_names.split(column_delimiter)]
            logger.debug(
                "Loading file: path=%s, delimiter=%s, skip_rows=%s, columns_names=%s",
                self.file_path,
                self.delimiter,
                self.skip_rows,
                columns_names,
            )
        else:
            logger.debug(
                "Loading file: path=%s, delimiter=%s, skip_rows=%s, columns_names=none",
                self.file_path,
                self.delimiter,
                self.skip_rows,
            )

        # Determine file extension and load accordingly.
        _, file_extension = os.path.splitext(self.file_path)

        # Additional console output to inform user that file loading is in progress.
        console.log(f"\n\nAttempting to load the file: {self.file_path}")

        if file_extension == ".csv":
            self.load_csv()
        elif file_extension == ".txt":
            self.load_txt()
        else:
            console.log(f"\n\nFile extension '{file_extension}' is not supported.")

        self.loaded_files.add(self.file_path)
        # Inform user that file loading is complete.
        console.log(f"\n\nFile '{self.file_path}' has been successfully loaded.")

    @detect_encoding
    @detect_decimal
    def load_csv(self, **kwargs):
        """
        Load a CSV file into a pandas DataFrame using the detected encoding
        and decimal separator.

        Parameters
        ----------
        **kwargs : dict
            Additional keyword arguments for pandas.read_csv (encoding, decimal, etc.).
        """
        try:
            # Using 'engine="python"' to handle more complex separators and formats.
            self.data = pd.read_csv(
                self.file_path,
                sep=self.delimiter,
                engine="python",
                on_bad_lines="skip",
                skiprows=self.skip_rows,
                header=0,
                **kwargs,
            )
            self._fetch_data()
        except Exception as e:
            logger.error(f"Error while loading CSV file: {e}")
            console.log("\n\nError: Unable to load the CSV file.")

    @detect_encoding
    @detect_decimal
    def load_txt(self, **kwargs):
        """
        Load a TXT file into a pandas DataFrame using the detected encoding
        and decimal separator.

        Parameters
        ----------
        **kwargs : dict
            Additional keyword arguments for pandas.read_table (encoding, decimal, etc.).
        """
        try:
            self.data = pd.read_table(
                self.file_path,
                sep=self.delimiter,
                skiprows=self.skip_rows,
                header=0,
                **kwargs,
            )
            self._fetch_data()
        except Exception as e:
            logger.error(f"Error while loading TXT file: {e}")
            console.log("\n\nError: Unable to load the TXT file.")

    def _fetch_data(self):
        """
        Finalize data loading process: apply column names if provided,
        store original and copy of the DataFrame, and emit signal.

        In complex scenarios, we first ensure that the number of provided
        column names matches the number of columns in the DataFrame.
        Otherwise, a warning is logged. If column names are not provided,
        the first row of the file is used as column headers by default.

        This method also logs DataFrame info for debug and emits the
        data_loaded_signal.
        """
        file_basename = os.path.basename(self.file_path)

        # If user-specified column names are provided, ensure they match the dataframe columns count.
        if self.columns_names is not None:
            if len(self.columns_names) != len(self.data.columns):
                logger.warning("The number of user-provided column names does not match the dataset columns.")
            # Attempt to convert all columns to numeric where possible.
            self.data = self.data.apply(pd.to_numeric, errors="coerce")
            self.data.columns = [name.strip() for name in self.columns_names]
        else:
            logger.debug("No custom column names provided; using file's header row as column names.")

        # Store original and copy of the data for transformations.
        self.original_data[file_basename] = self.data.copy()
        self.dataframe_copies[file_basename] = self.data.copy()

        # Log DataFrame info to console for user reference.
        buffer = StringIO()
        self.dataframe_copies[file_basename].info(buf=buffer)
        file_info = buffer.getvalue()
        console.log(f"\n\nFile loaded:\n{file_info}")

        logger.debug(f"dataframe_copies keys: {self.dataframe_copies.keys()}")
        # Emit a signal that data is loaded.
        self.data_loaded_signal.emit(self.data)

    @pyqtSlot(str)
    def plot_dataframe_copy(self, key):
        """
        Request plotting of a dataframe copy identified by 'key'.

        Parameters
        ----------
        key : str
            The key identifying the dataframe copy to plot.
        """
        if key in self.dataframe_copies:
            # Handle request to plot using the dispatcher.
            # This might involve complex logic, so we rely on another system (handle_request_cycle).
            _ = self.handle_request_cycle("main_window", "plot_df", df=self.dataframe_copies[key])
            console.log(f"\n\nPlotting the DataFrame with key: {key}")
        else:
            logger.error(f"Key '{key}' not found in dataframe_copies.")

    def reset_dataframe_copy(self, key):
        """
        Reset the dataframe copy identified by 'key' back to the original
        loaded data. Also clears any operation history associated with
        this key.

        Parameters
        ----------
        key : str
            The key identifying the dataframe copy to reset.
        """
        if key in self.original_data:
            self.dataframe_copies[key] = self.original_data[key].copy()
            if key in self.operations_history:
                del self.operations_history[key]
            logger.debug(f"Reset data for key '{key}' and cleared operations history.")
            console.log(f"\n\nData reset for '{key}'. Original state restored.")

    def modify_data(self, func, params):
        """
        Apply a modification function 'func' to all columns of the
        dataframe copy identified by 'file_name', except columns named 'temperature'.

        Parameters
        ----------
        func : callable
            A function that takes a pandas Series and returns a modified Series.
        params : dict
            A dictionary with details of the operation, including 'file_name'.

        Notes
        -----
        This method logs the operation, updates the operations history,
        and allows chaining modifications without losing previous state.
        """
        file_name = params.get("file_name")
        if not callable(func):
            logger.error("The provided 'func' is not callable.")
            console.log("\n\nError: Provided function is not callable.")
            return

        if file_name not in self.dataframe_copies:
            logger.error(f"Key '{file_name}' not found in dataframe_copies.")
            console.log("\n\nError: Cannot modify data as the file was not found in memory.")
            return

        try:
            dataframe = self.dataframe_copies[file_name]
            # Modify all columns except 'temperature'
            for column in dataframe.columns:
                if column != "temperature":
                    dataframe[column] = func(dataframe[column])

            self.log_operation(params)
            logger.info("Data has been successfully modified.")

        except Exception as e:
            logger.error(f"Error modifying data for file '{file_name}': {e}")

    def process_request(self, params: dict):
        """
        Process a request dictionary that includes 'operation', 'file_name',
        and potentially a 'function' for data modification. Depending on
        the operation, this method may modify data, reset data, load files,
        or return information about the data.

        Parameters
        ----------
        params : dict
            Dictionary representing the request. Must contain 'operation' and 'file_name'.
            It may also contain 'function', 'actor', 'target', and others.

        Supported operations include:
        - "differential": Apply a differential modification if not done before.
        - "check_differential": Check if differential operation was performed.
        - "get_df_data": Retrieve the current DataFrame copy.
        - "reset": Reset the DataFrame to its original state.
        - "load_file": Load a file.

        After processing, 'params' is modified to include 'data' key
        with the operation result and the roles of 'actor' and 'target'
        are swapped. Finally, the signals.response_signal is emitted.
        """
        operation = params.get("operation")
        file_name = params.get("file_name")
        func = params.get("function")
        actor = params.get("actor")

        logger.debug(f"{self.actor_name} processing request '{operation}' from '{actor}'")

        if not file_name:
            logger.error("No 'file_name' specified in the request.")
            console.log("\n\nError: 'file_name' must be specified for the requested operation.")
            return

        # Perform operation based on the request.
        if operation == "differential":
            if not self.check_operation_executed(file_name, "differential"):
                self.modify_data(func, params)
            else:
                console.log("\n\nThe data has already been transformed (differential operation).")
            params["data"] = True

        elif operation == "check_differential":
            params["data"] = self.check_operation_executed(file_name, "differential")

        elif operation == "get_df_data":
            params["data"] = self.dataframe_copies.get(file_name)
            if params["data"] is None:
                console.log(f"\n\nNo data found for file '{file_name}'.")

        elif operation == "reset":
            self.reset_dataframe_copy(file_name)
            params["data"] = True

        elif operation == "load_file":
            # Here we assume the request 'file_name' actually contains the tuple
            # (file_path, delimiter, skip_rows, columns_names).
            # This is part of the communication protocol outside the class scope.
            self.load_file(file_name)
            params["data"] = True

        else:
            console.log(f"\n\nUnknown operation '{operation}'. No action taken.")
            return

        params["target"], params["actor"] = params.get("actor"), params.get("target")

        self.signals.response_signal.emit(params)
