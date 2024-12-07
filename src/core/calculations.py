"""
This module provides the `Calculations` class, which manages the execution of deconvolution
calculations, including parameter optimization through methods like differential evolution.
It integrates with other components such as the dispatcher and utilizes signals for
asynchronous updates. The class also handles the logging of intermediate and best
results during the optimization process.
"""

from typing import Callable

import numpy as np
import pandas as pd
from PyQt6.QtCore import pyqtSignal, pyqtSlot
from scipy.optimize import OptimizeResult, differential_evolution

from src.core.basic_signals import BasicSignals
from src.core.calculation_thread import CalculationThread
from src.core.curve_fitting import CurveFitting as cft
from src.core.logger_config import logger
from src.core.logger_console import LoggerConsole as console


class Calculations(BasicSignals):
    """
    Manages the calculation processes for reaction parameter deconvolution and optimization.

    This class handles:
    - Initiating calculation threads.
    - Performing differential evolution optimization.
    - Emitting signals when new best results are found.
    - Formatting and logging the results of parameter optimization.

    Attributes:
        new_best_result (pyqtSignal): Emitted when a new best result is found\
            (dict containing 'best_mse', 'best_combination', 'params').
        thread (CalculationThread): The currently running calculation thread, if any.
        differential_evolution_results (list[tuple[np.ndarray, float]]):\
            Stores intermediate results from differential evolution.
        best_combination (tuple): The best combination of reaction functions found so far.
        best_mse (float): The best (lowest) mean squared error found so far.
    """

    new_best_result = pyqtSignal(dict)

    def __init__(self, dispatcher):
        """
        Initialize the Calculations instance.

        Args:
            dispatcher: The dispatcher object for inter-component communication.
        """
        super().__init__(actor_name="calculations", dispatcher=dispatcher)
        self.thread: CalculationThread = None
        self.differential_evolution_results: list[tuple[np.ndarray, float]] = []
        self.best_combination = None
        self.best_mse = float("inf")
        self.new_best_result.connect(self.handle_new_best_result)

    def start_calculation_thread(self, func: Callable, *args, **kwargs) -> None:
        """
        Start a new calculation thread with the given function and arguments.

        Args:
            func (Callable): The function to run in the calculation thread.
            *args: Variable positional arguments for the function.
            **kwargs: Variable keyword arguments for the function.
        """
        self.thread = CalculationThread(func, *args, **kwargs)
        self.thread.result_ready.connect(self._calculation_finished)
        self.thread.start()
        # Removed unnecessary logs as per the request

    @pyqtSlot(dict)
    def process_request(self, params: dict):
        """
        Process incoming requests. Currently, this method is not implemented.

        Args:
            params (dict): Parameters for request handling.
        """
        logger.debug("process_request called with no implemented logic.")
        pass

    @pyqtSlot(object)
    def _calculation_finished(self, result):
        """
        Handle the signal when a calculation finishes.

        Args:
            result (object): The result from the calculation, which can be an OptimizeResult or another object.
        """
        try:
            if isinstance(result, OptimizeResult):
                x = result.x
                fun = result.fun
                success = result.success
                message = result.message

                logger.info("Optimization finished with an OptimizeResult.")
                console.log(
                    f"Calculation completed successfully.\n"
                    f"Optimal parameters: {x}\n"
                    f"Objective function value: {fun}\n"
                    f"Success status: {success}\n"
                    f"Message: {message}"
                )

                self.best_combination = x
                self.best_mse = fun
            else:
                logger.info("Calculation finished with a non-OptimizeResult object.")
                console.log(f"Calculation completed successfully. Result: {result}")

        except ValueError as e:
            logger.error(f"Error processing the result: {e}")
            console.log("An error occurred while processing the calculation result. Check logs for details.")

    @pyqtSlot(dict)
    def run_deconvolution(self, response: dict):
        """
        Prepare and execute the deconvolution process.

        This sets up the target function and starts the chosen optimization method (e.g., differential_evolution).

        Args:
            response (dict): Must contain:
                - "reaction_variables": dict of reactions and their variables.
                - "bounds": parameter bounds for optimization.
                - "reaction_combinations": list of tuples indicating different reaction function combos.
                - "experimental_data": pandas DataFrame with experimental data.
                - "deconvolution_settings": dict with method and parameters for the optimization.
        """
        logger.debug(f"run_deconvolution called with response: {response}")
        # Removed unnecessary logs as per the request
        try:
            reaction_variables = response["reaction_variables"]
            bounds = response["bounds"]
            reaction_combinations = response["reaction_combinations"]
            experimental_data = response["experimental_data"]
            deconvolution_settings: dict = response["deconvolution_settings"]
            deconvolution_method = deconvolution_settings.pop("method", "")
            deconvolution_parameters = deconvolution_settings.pop("deconvolution_parameters", {})

            target_function = self.generate_target_function(
                reaction_variables, reaction_combinations, experimental_data
            )

            if deconvolution_method == "differential_evolution":
                logger.info("Starting differential evolution optimization.")
                self.start_differential_evolution(
                    bounds=bounds, target_function=target_function, **deconvolution_parameters
                )
            else:
                logger.error(f"Unknown deconvolution method: {deconvolution_method}")
                console.log("Error: Unknown deconvolution method requested. Check logs.")

        except Exception as e:
            logger.error(f"Error preparing and starting optimization: {e}")
            console.log("Error preparing and starting optimization. Check logs for details.")

    def generate_target_function(
        self,
        combined_keys: dict,
        reaction_combinations: list[tuple],
        experimental_data: pd.DataFrame,
    ):
        """
        Generate the target function for optimization. This function calculates
        the MSE (mean squared error) between the cumulative function of chosen
        reactions and the experimental data, and updates the best result if a new
        best combination is found.

        Args:
            combined_keys (dict): Reaction variables mapping for each reaction.
            reaction_combinations (list[tuple]): Each tuple represents a combination of reaction function types.
            experimental_data (pd.DataFrame): The input experimental data.

        Returns:
            Callable: The target function used by the optimization routine.
        """

        def target_function(params):
            best_mse = float("inf")
            best_combination = None

            # Iterate through each combination of reactions
            for combination in reaction_combinations:
                cumulative_function = np.zeros(len(experimental_data["temperature"]))
                param_idx = 0

                # Construct the cumulative function from each reaction in the combination
                for (reaction, coeffs), func in zip(combined_keys.items(), combination):
                    coeff_count = len(coeffs)
                    func_params = params[param_idx : param_idx + coeff_count]
                    param_idx += coeff_count

                    x = experimental_data["temperature"]

                    # For all functions, first three params are h, z, w
                    if len(func_params) < 3:
                        raise ValueError("Not enough parameters for the function.")
                    h, z, w = func_params[0:3]

                    # Based on the function type, parse additional parameters if needed
                    if func == "gauss":
                        reaction_values = cft.gaussian(x, h, z, w)
                        cumulative_function += reaction_values

                    if func == "fraser":
                        # fraser_suzuki requires 'fr' after h,z,w
                        fr = func_params[3]
                        reaction_values = cft.fraser_suzuki(x, h, z, w, fr)
                        cumulative_function += reaction_values

                    if func == "ads":
                        # ads requires ads1 and ads2 after h,z,w
                        ads1 = func_params[3]
                        ads2 = func_params[4]
                        reaction_values = cft.asymmetric_double_sigmoid(x, h, z, w, ads1, ads2)
                        cumulative_function += reaction_values

                y_true = experimental_data.iloc[:, 1].to_numpy()
                mse = np.mean((y_true - cumulative_function) ** 2)
                # If this combination is better, update the best known result
                if mse < best_mse:
                    best_mse = mse
                    best_combination = combination
                    self.new_best_result.emit(
                        {"best_mse": best_mse, "best_combination": best_combination, "params": params}
                    )

            return best_mse

        return target_function

    def start_differential_evolution(self, bounds, *args, **kwargs):
        """
        Start differential evolution optimization in a separate thread.

        Args:
            bounds (list[tuple]): Bounds for the parameters.
            *args: Additional positional arguments.
            **kwargs: Must contain 'target_function' key. Additional keyword arguments for differential_evolution.
        """
        if "target_function" not in kwargs:
            raise ValueError("Must provide 'target_function' in kwargs for differential evolution.")
        target_function = kwargs.pop("target_function")

        logger.debug(f"Starting differential evolution with bounds: {bounds} and kwargs: {kwargs}")

        self.start_calculation_thread(
            differential_evolution,
            target_function,
            bounds=bounds,
            **kwargs,
        )

    def _save_intermediate_result(self, xk, convergence):
        """
        Save intermediate optimization results from differential evolution.

        Args:
            xk (np.ndarray): Current parameter vector.
            convergence (float): Convergence measure from differential evolution.
        """
        self.differential_evolution_results.append((xk, convergence))
        logger.info(f"Intermediate result: xk = {xk}, convergence = {convergence}")

    @pyqtSlot(dict)
    def handle_new_best_result(self, result: dict):
        """
        Handle the signal when a new best result is found during optimization.

        This method formats and logs the best MSE, combination, and parameters in a YAML-like structure.

        Args:
            result (dict): Contains 'best_mse', 'best_combination', and 'params'.
        """
        best_mse = result["best_mse"]
        best_combination = result["best_combination"]
        params = result["params"]

        if best_mse < self.best_mse:
            self.best_mse = best_mse
            self.best_combination = best_combination

            logger.info("A new best result has been found.")

            # Determine table structure based on the combination of functions
            # Each reaction always has h, z, w. Additional parameters depend on the function type.
            # gauss: h, z, w (3 params)
            # fraser: h, z, w, fr (4 params)
            # ads: h, z, w, ads1, ads2 (5 params)
            #
            # We will print the parameters in a YAML-like format:
            #
            # parameters:
            #   r1:
            #     h: <val>
            #     z: <val>
            #     w: <val>
            #     fr/NAN: <val or null>
            #     ads1/NAN: <val or null>
            #     ads2/NAN: <val or null>
            #   r2:
            #     ...
            #
            def reaction_param_count(func_type):
                if func_type == "gauss":
                    return 3
                elif func_type == "fraser":
                    return 4
                elif func_type == "ads":
                    return 5
                else:
                    return 3  # default if unknown

            # # Parse parameters according to each reaction function
            # reaction_count = len(best_combination)
            # column_labels = ["h", "z", "w", "fr", "ads1", "ads2"]

            idx = 0
            parameters_yaml = "parameters:\n"
            for i, func_type in enumerate(best_combination, start=1):
                count = reaction_param_count(func_type)
                reaction_params = params[idx : idx + count]
                idx += count

                # Build a dict of param_name -> value
                # Start with h,z,w always
                param_dict = {
                    "h": float(reaction_params[0]),
                    "z": float(reaction_params[1]),
                    "w": float(reaction_params[2]),
                    "fr": None,
                    "ads1": None,
                    "ads2": None,
                }

                if func_type == "fraser":
                    param_dict["fr"] = float(reaction_params[3])
                elif func_type == "ads":
                    param_dict["ads1"] = float(reaction_params[3])
                    param_dict["ads2"] = float(reaction_params[4])

                # Append to parameters_yaml
                parameters_yaml += f"  r{i}:\n"
                for k, v in param_dict.items():
                    val_str = "null" if v is None else f"{v}"
                    parameters_yaml += f"    {k}: {val_str}\n"

            console.log("New best result found:")
            console.log(f"Best MSE: {best_mse}")
            console.log(f"Reaction combination: {best_combination}")
            console.log("Reaction parameters have been updated based on the best combination found.")
            console.log("Parameters in YAML-like format:")
            console.log(parameters_yaml.rstrip())

            file_name = self.handle_request_cycle("main_window", "get_file_name")
            self.handle_request_cycle(
                "calculations_data_operations",
                "update_reactions_params",
                path_keys=[file_name],
                best_combination=best_combination,
                reactions_params=params,
            )

    @pyqtSlot(bool)
    def calc_data_operations_in_progress(self, in_progress: bool):
        """
        Slot to handle when calculations_data_operations are in progress.

        Args:
            in_progress (bool): True if calculations are in progress, False otherwise.
        """
        # Removed unnecessary logs as per the request
        if in_progress:
            logger.debug("Calculations data operations are now in progress.")
        else:
            logger.debug("Calculations data operations have completed.")
