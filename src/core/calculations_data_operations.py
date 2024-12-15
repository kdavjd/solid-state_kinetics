"""
This module provides the `CalculationsDataOperations` class for processing and handling
reaction data, performing operations such as adding, removing, highlighting reactions,
and managing deconvolution tasks. It integrates with a dispatcher for inter-component
communication, uses a signal-based architecture for asynchronous updates, and interacts
with other core functionalities like curve fitting.
"""

import time
from itertools import product

import numpy as np
from core.base_signals import BaseSlots
from PyQt6.QtCore import pyqtSignal, pyqtSlot

from src.core.curve_fitting import CurveFitting as cft
from src.core.logger_config import logger
from src.core.logger_console import LoggerConsole as console


class CalculationsDataOperations(BaseSlots):
    """
    Handles calculations and data operations for reaction parameters and related actions.

    This class processes requests such as adding or removing reactions,
    updating values, performing deconvolution, and updating reaction parameters. It also
    emits signals for GUI updates, including reaction plots and parameter emissions.

    Attributes:
        deconvolution_signal (pyqtSignal): Signal emitted with deconvolution result (dict).
        plot_reaction (pyqtSignal): Signal emitted to plot a reaction curve (tuple, list).
        reaction_params_to_gui (pyqtSignal): Signal emitted to send reaction parameters to the GUI.
        last_plot_time (float): Timestamp of the last reaction plot update.
        calculations_in_progress (bool): Indicates if a calculation process is ongoing.
        reaction_variables (dict): Mapping of reaction names to sets of variable keys.
        reaction_chosen_functions (dict[str, list]): Mapping of reaction names to chosen function types.
    """

    deconvolution_signal = pyqtSignal(dict)
    plot_reaction = pyqtSignal(tuple, list)
    reaction_params_to_gui = pyqtSignal(dict)

    def __init__(self, signals):
        super().__init__(actor_name="calculations_data_operations", signals=signals)
        self.last_plot_time = 0
        self.calculations_in_progress = False
        self.reaction_variables: dict = {}
        self.reaction_chosen_functions: dict[str, list] = {}

    @pyqtSlot(dict)
    def process_request(self, params: dict):
        """
        Process incoming requests related to reaction data operations.

        Args:
            params (dict): Parameters dict with 'path_keys', 'operation', and additional details.
        """
        path_keys = params.get("path_keys")
        operation = params.get("operation")

        if not path_keys or not isinstance(path_keys, list):
            logger.error("Invalid or empty path_keys list.")
            return

        operations = {
            "add_reaction": self.add_reaction,
            "remove_reaction": self.remove_reaction,
            "highlight_reaction": self.highlight_reaction,
            "update_value": self.update_value,
            "deconvolution": self.deconvolution,
            "update_reactions_params": self.update_reactions_params,
        }

        if operation in operations:
            params["data"] = True
            logger.debug(f"Processing operation '{operation}' with path_keys: {path_keys}")
            answer = operations[operation](path_keys, params)

            # Perform additional actions after the main operation if needed
            if answer:
                if operation == "update_value":
                    self._protected_plot_update_curves(path_keys, params)
                if operation == "deconvolution":
                    self.deconvolution_signal.emit(answer)

            # Swap target and actor before emitting the response
            params["target"], params["actor"] = params["actor"], params["target"]
            self.signals.response_signal.emit(params)
        else:
            logger.warning("Unknown or missing data operation.")

    def _protected_plot_update_curves(self, path_keys, params):
        """
        Update reaction curves if not currently in progress and a sufficient
        time interval has passed since the last plot.

        Args:
            path_keys (list): Keys defining the data path.
            params (dict): Additional parameters.
        """
        if self.calculations_in_progress:
            # If calculations are ongoing, we skip updating to prevent UI overload
            logger.debug("Skipping plot update as calculations are in progress.")
            return
        current_time = time.time()
        # Update only if at least 0.1 seconds have passed since the last plot
        if current_time - self.last_plot_time >= 0.1:
            self.last_plot_time = current_time
            logger.debug("Updating reaction curves based on updated values.")
            self.highlight_reaction(path_keys, params)

    def _extract_reaction_params(self, path_keys: list):
        """
        Extract reaction parameters from the calculations data.

        Args:
            path_keys (list): Keys to locate the reaction data.

        Returns:
            dict: Parsed reaction parameters from the given path keys.
        """
        reaction_params = self.handle_request_cycle("calculations_data", "get_value", path_keys=path_keys)
        return cft.parse_reaction_params(reaction_params)

    def _plot_reaction_curve(self, file_name, reaction_name, bound_label, params):
        """
        Plot a reaction curve for given reaction parameters and emit the plot signal.

        Args:
            file_name (str): Name of the file associated with the reaction.
            reaction_name (str): Name of the reaction.
            bound_label (str): Label for the bound coefficients (e.g., 'coeffs', 'upper_bound_coeffs').
            params (list): Reaction parameters used for plotting.
        """
        if not params:
            logger.warning(f"No parameters found for {reaction_name} with bound {bound_label}. Skipping plot.")
            return
        x_min, x_max = params[0]
        x = np.linspace(x_min, x_max, 100)
        y = cft.calculate_reaction(params)
        curve_name = f"{reaction_name}_{bound_label}"
        logger.debug(f"Emitting plot signal for curve: {curve_name} in file: {file_name}.")
        self.plot_reaction.emit((file_name, curve_name), [x, y])

    def update_reactions_params(self, path_keys: list, params: dict):
        """
        Update reaction parameters based on the provided best combination of functions and parameter values.

        Args:
            path_keys (list): Keys to locate the data (usually includes file name).
            params (dict): Contains 'best_combination' and 'reactions_params' for updating reactions.
        """
        file_name = path_keys[0]
        reaction_functions: tuple[str] = params.get("best_combination", None)
        reactions_params = params.get("reactions_params", None)
        if reaction_functions is None or reactions_params is None:
            logger.error("Missing 'best_combination' or 'reactions_params' for update.")
            console.log("Error: Unable to update reaction parameters due to missing required data.")
            return

        n_reactions_coeffs = [len(self.reaction_variables[key]) for key in self.reaction_variables]
        reactions_dict = {}
        start = 0
        for key, count in zip(self.reaction_variables.keys(), n_reactions_coeffs):
            reactions_dict[key] = reactions_params[start : start + count]
            start += count

        ordered_vars = ["h", "z", "w", "fr", "ads1", "ads2"]
        sorted_reactions = sorted(reactions_dict.keys(), key=lambda x: int(x.split("_")[1]))

        # Updating parameters for each reaction and their allowed variables
        for i, reaction in enumerate(sorted_reactions):
            variables = self.reaction_variables[reaction]
            values = reactions_dict[reaction]
            function_type = reaction_functions[i]
            allowed_keys = cft._get_allowed_keys_for_type(function_type)
            var_list = [var for var in ordered_vars if var in variables and var in allowed_keys]

            for var, value in zip(var_list, values):
                for bound in ["lower_bound_coeffs", "coeffs", "upper_bound_coeffs"]:
                    pk = [file_name, reaction, bound, var]
                    pr = {"value": value, "is_chain": True}
                    self.update_value(pk, pr)

        logger.info("Reaction parameters updated successfully.")
        console.log("Reaction parameters have been updated based on the best combination found.")

    def add_reaction(self, path_keys: list, _params: dict):
        """
        Add a new reaction to the calculations data and plot its initial curves.

        Args:
            path_keys (list): [file_name, reaction_name].
            _params (dict): Additional parameters (unused directly).
        """
        file_name, reaction_name = path_keys

        # Check if differential data is available before adding the reaction
        is_executed = self.handle_request_cycle("file_data", "check_differential", file_name=file_name)

        if is_executed:
            df = self.handle_request_cycle("file_data", "get_df_data", file_name=file_name)
            data = cft.generate_default_function_data(df)
            is_exist = self.handle_request_cycle(
                "calculations_data", "set_value", path_keys=path_keys.copy(), value=data
            )
            if is_exist:
                logger.warning(f"Data already exists at path: {path_keys.copy()} - overwriting not performed.")

            # Extract reaction parameters and plot them
            reaction_params = self._extract_reaction_params(path_keys)
            for bound_label, params in reaction_params.items():
                self._plot_reaction_curve(file_name, reaction_name, bound_label, params)
            console.log(f"Reaction '{reaction_name}' has been successfully added to file '{file_name}'.")
        else:
            _params["data"] = False
            logger.error(f"Differential data check failed for file: {file_name}. Cannot add reaction.")
            console.log(f"Failed to add reaction '{reaction_name}' due to missing differential data in '{file_name}'.")

    def remove_reaction(self, path_keys: list, _params: dict):
        """
        Remove a reaction from the calculations data.

        Args:
            path_keys (list): [file_name, reaction_name].
            _params (dict): Additional parameters (unused directly).
        """
        if len(path_keys) < 2:
            logger.error("Insufficient path_keys information to remove reaction.")
            return
        file_name, reaction_name = path_keys
        is_exist = self.handle_request_cycle("calculations_data", "remove_value", path_keys=path_keys)
        if not is_exist:
            logger.warning(f"Reaction {reaction_name} not found in data.")
            console.log(f"Reaction '{reaction_name}' could not be found for removal.")
        else:
            logger.debug(f"Removed reaction {reaction_name} for file {file_name}.")
            console.log(f"Reaction '{reaction_name}' was successfully removed from file '{file_name}'.")

    def highlight_reaction(self, path_keys: list, _params: dict):
        """
        Highlight the selected reaction by plotting individual reaction curves and cumulative curves.

        Args:
            path_keys (list): Keys specifying the file and possibly the reaction to highlight.
            _params (dict): Additional parameters (unused directly).
        """
        file_name = path_keys[0]
        data = self.handle_request_cycle("calculations_data", "get_value", path_keys=[file_name])

        if not data:
            logger.warning(f"No data found for file '{file_name}' when highlighting reaction.")
            console.log(f"No data available for highlighting reactions in file '{file_name}'.")
            return

        reactions = data.keys()

        # Initialize cumulative storage for the sum of all reactions' Y-values
        cumulative_y = {
            "upper_bound_coeffs": np.array([]),
            "lower_bound_coeffs": np.array([]),
            "coeffs": np.array([]),
        }
        x = None

        # Iterate through reactions to plot and accumulate results
        for reaction_name in reactions:
            reaction_params = self._extract_reaction_params([file_name, reaction_name])
            # Calculate and accumulate results for each bound type
            for bound_label, params in reaction_params.items():
                if bound_label in cumulative_y:
                    # Calculate Y-values for the current reaction and bound
                    y = cft.calculate_reaction(reaction_params.get(bound_label, []))
                    if x is None:
                        x_min, x_max = params[0]
                        x = np.linspace(x_min, x_max, 100)
                    cumulative_y[bound_label] = cumulative_y[bound_label] + y if cumulative_y[bound_label].size else y

            # If reaction_name is specified in path_keys, treat it as highlighted
            if reaction_name in path_keys:
                self.reaction_params_to_gui.emit(reaction_params)
                logger.debug(f"Highlighting reaction: {reaction_name}")
                # Plot the upper and lower bound curves explicitly for the highlighted reaction
                self._plot_reaction_curve(
                    file_name, reaction_name, "upper_bound_coeffs", reaction_params.get("upper_bound_coeffs", [])
                )
                self._plot_reaction_curve(
                    file_name, reaction_name, "lower_bound_coeffs", reaction_params.get("lower_bound_coeffs", [])
                )
            else:
                # For non-highlighted reactions, plot only the 'coeffs' curve
                self._plot_reaction_curve(file_name, reaction_name, "coeffs", reaction_params.get("coeffs", []))

        # Plot the cumulative curves once all reactions are processed
        if x is not None:
            for bound_label, y in cumulative_y.items():
                self.plot_reaction.emit((file_name, f"cumulative_{bound_label}"), [x, y])
            logger.info("Cumulative curves have been plotted.")

    def _update_coeffs_value(self, path_keys: list[str], new_value):
        """
        Update the middle 'coeffs' value based on changes in 'upper_bound_coeffs' or
        'lower_bound_coeffs' to maintain consistency.

        Args:
            path_keys (list[str]): Keys indicating the exact coefficient path.
            new_value (float): The new value to set.
        """
        bound_keys = ["upper_bound_coeffs", "lower_bound_coeffs"]
        for key in bound_keys:
            if key in path_keys:
                # Identify the opposite bound key
                opposite_key = bound_keys[1 - bound_keys.index(key)]
                new_keys = path_keys.copy()
                # Replace the current bound key with the opposite one to fetch its value
                new_keys[new_keys.index(key)] = opposite_key

                # Retrieve the opposite bound's value to compute the average
                opposite_value = self.handle_request_cycle("calculations_data", "get_value", path_keys=new_keys)

                # Handle potential None or missing data gracefully
                if opposite_value is None:
                    logger.warning(f"Opposite bound data not found at {new_keys}. Cannot update coeffs.")
                    return

                average_value = (new_value + opposite_value) / 2
                # Now update to 'coeffs'
                new_keys[new_keys.index(opposite_key)] = "coeffs"
                is_exist = self.handle_request_cycle(
                    "calculations_data", "set_value", path_keys=new_keys, value=average_value
                )
                if is_exist:
                    logger.info(f"Data at {new_keys} updated to {average_value}.")
                else:
                    logger.error(f"No data found at {new_keys} for updating coeffs.")

    def update_value(self, path_keys: list[str], params: dict):
        """
        Update a specific value in the calculations data.

        Args:
            path_keys (list[str]): Keys identifying the target data path.
            params (dict): Contains 'value' to set and optional 'is_chain' bool.

        Returns:
            dict or None: Returns a dict indicating the operation if successful and not chained.
        """
        try:
            new_value = params.get("value")
            is_chain = params.get("is_chain", None)
            is_ok = self.handle_request_cycle(
                "calculations_data", "set_value", path_keys=path_keys.copy(), value=new_value
            )
            if is_ok:
                logger.debug(f"Data at {path_keys} updated to {new_value}.")
                if not is_chain:
                    # Update coeffs to keep consistency if bounds changed
                    self._update_coeffs_value(path_keys.copy(), new_value)
                    return {"operation": "update_value", "data": None}
            else:
                logger.error(f"No data found at {path_keys} for updating.")
        except ValueError as e:
            logger.error(f"Unexpected error updating data at {path_keys}: {str(e)}")

    def deconvolution(self, path_keys: list[str], params: dict):
        """
        Prepare and return data required for deconvolution, including reaction variables,
        chosen functions, bounds, and experimental data.

        Args:
            path_keys (list[str]): Keys, typically [file_name].
            params (dict): Must contain 'deconvolution_settings' and 'chosen_functions'.

        Returns:
            dict: Information needed to perform the deconvolution process.
        """
        deconvolution_settings = params.get("deconvolution_settings", {})
        reaction_variables = {}
        num_coefficients = {}
        bounds = []
        check_keys = ["h", "z", "w", "fr", "ads1", "ads2"]
        file_name = path_keys[0]
        reaction_chosen_functions: dict = params.get("chosen_functions", {})

        if not reaction_chosen_functions:
            raise ValueError("chosen_functions is None or empty")

        functions_data = self.handle_request_cycle("calculations_data", "get_value", path_keys=[file_name])
        if not functions_data:
            raise ValueError(f"No functions data found for file: {file_name}")

        # Generate all possible combinations of chosen reaction functions
        reaction_combinations = list(product(*reaction_chosen_functions.values()))

        # Determine variables and bounds for each reaction
        for reaction_name in reaction_chosen_functions:
            function_vars = set()
            reaction_params = functions_data[reaction_name]
            if not reaction_params:
                raise ValueError(f"No reaction params found for reaction: {reaction_name}")
            for reaction_type in reaction_chosen_functions[reaction_name]:
                allowed_keys = cft._get_allowed_keys_for_type(reaction_type)
                function_vars.update(allowed_keys)
            reaction_variables[reaction_name] = function_vars

            lower_coeffs = reaction_params["lower_bound_coeffs"].values()
            upper_coeffs = reaction_params["upper_bound_coeffs"].values()
            # Filter pairs of lower/upper that correspond to allowed variables
            filtered_pairs = [
                (lc, uc) for lc, uc, key in zip(lower_coeffs, upper_coeffs, check_keys) if key in function_vars
            ]
            bounds.extend(filtered_pairs)
            num_coefficients[reaction_name] = len(function_vars)

        df = self.handle_request_cycle("file_data", "get_df_data", file_name=file_name)
        self.reaction_variables = reaction_variables.copy()
        self.reaction_chosen_functions = reaction_chosen_functions.copy()

        logger.info(f"Preparing for deconvolution with reaction_variables: {reaction_variables}")
        console.log("Preparing reaction data for deconvolution. Please wait...")

        return {
            "reaction_variables": reaction_variables,
            "deconvolution_settings": deconvolution_settings,
            "bounds": bounds,
            "reaction_combinations": reaction_combinations,
            "experimental_data": df,
        }
