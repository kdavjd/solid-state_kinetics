from typing import Callable, Optional

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
        super().__init__(actor_name="calculations", dispatcher=dispatcher)
        self.differential_evolution_results: list[tuple[np.ndarray, float]] = []
        self.thread: Optional[CalculationThread] = None
        self.best_combination: Optional[tuple] = None
        self.best_mse: float = float("inf")
        self.new_best_result.connect(self.handle_new_best_result)

    def start_calculation_thread(self, func: Callable, *args, **kwargs) -> None:
        self.thread = CalculationThread(func, *args, **kwargs)
        self.thread.result_ready.connect(self._calculation_finished)
        self.thread.start()

    @pyqtSlot(dict)
    def process_request(self, params: dict):
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
    def handle_new_best_result(self, result: dict):  # noqa: C901
        """
        Handles the event when a new best result is found during optimization.

        This method updates the best MSE and combination if the new result is better.
        It formats and logs the best MSE, combination, and parameters in a YAML-like structure
        with each parameter rounded to four decimal places.

        Args:
            result (dict): A dictionary containing 'best_mse', 'best_combination', and 'params'.
                        - 'best_mse' (float): The best Mean Squared Error achieved.
                        - 'best_combination' (list[str]): The combination of reaction functions.
                        - 'params' (list[float]): The parameters corresponding to the best combination.
        """
        best_mse = result["best_mse"]
        best_combination = result["best_combination"]
        params = result["params"]

        if best_mse < self.best_mse:
            self.best_mse = best_mse
            self.best_combination = best_combination

            logger.info("A new best result has been found.")

            def reaction_param_count(func_type: str) -> int:
                """
                Determines the number of parameters based on the reaction function type.

                Args:
                    func_type (str): The type of reaction function.

                Returns:
                    int: The number of parameters for the given function type.
                """
                if func_type == "gauss":
                    return 3
                elif func_type == "fraser":
                    return 4
                elif func_type == "ads":
                    return 5
                else:
                    return 3  # Default to 3 if unknown

            idx = 0
            parameters_yaml = "parameters:\n"
            for i, func_type in enumerate(best_combination, start=1):
                count = reaction_param_count(func_type)
                reaction_params = params[idx : idx + count]
                idx += count

                # Initialize parameter dictionary with default None values
                param_dict = {
                    "h": None,
                    "z": None,
                    "w": None,
                    "fr": None,
                    "ads1": None,
                    "ads2": None,
                }

                # Assign values based on function type
                try:
                    param_dict["h"] = round(float(reaction_params[0]), 4)
                    param_dict["z"] = round(float(reaction_params[1]), 4)
                    param_dict["w"] = round(float(reaction_params[2]), 4)

                    if func_type == "fraser" and count >= 4:
                        param_dict["fr"] = round(float(reaction_params[3]), 4)
                    elif func_type == "ads" and count >= 5:
                        param_dict["ads1"] = round(float(reaction_params[3]), 4)
                        param_dict["ads2"] = round(float(reaction_params[4]), 4)
                except (IndexError, ValueError) as e:
                    logger.error(f"Error parsing parameters for reaction {i}: {e}")
                    continue  # Skip to the next reaction if there's an error

                # Append formatted parameters to YAML string
                parameters_yaml += f"  r{i}:\n"
                for key, value in param_dict.items():
                    val_str = "null" if value is None else f"{value:.4f}"
                    parameters_yaml += f"    {key}: {val_str}\n"

            # Log the formatted YAML parameters
            console.log("\nNew best result found:")
            console.log(f"\nBest MSE: {best_mse:.4f}")
            console.log(f"\nReaction combination: {best_combination}")
            console.log("\n\nReaction parameters have been updated based on the best combination found.")
            console.log(parameters_yaml.rstrip())

            # Retrieve the current file name from the main window
            file_name = self.handle_request_cycle("main_window", "get_file_name")
            # Update the reactions parameters in the calculations data operations
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
        if in_progress:
            logger.debug("Calculations data operations are now in progress.")
        else:
            logger.debug("Calculations data operations have completed.")
