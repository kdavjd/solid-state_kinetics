from typing import Callable, Optional

import numpy as np
import pandas as pd
from core.base_signals import BaseSlots
from PyQt6.QtCore import pyqtSignal, pyqtSlot
from scipy.optimize import OptimizeResult, differential_evolution

from src.core.calculation_thread import CalculationThread
from src.core.curve_fitting import CurveFitting as cft
from src.core.logger_config import logger
from src.core.logger_console import LoggerConsole as console
from src.core.result_strategies import BestResultStrategy, DeconvolutionStrategy, ModelBasedCalculationStrategy


class Calculations(BaseSlots):
    """
    Manages the calculation processes for reaction parameter deconvolution and optimization.

    This class handles:
    - Initiating calculation threads.
    - Performing differential evolution optimization.
    - Emitting signals when new best results are found.
    - Formatting and logging the results of parameter optimization.

    Attributes:
        new_best_result (pyqtSignal): Emitted when a new best result is found
            (dict containing 'best_mse', 'best_combination', 'params').
        thread (CalculationThread): The currently running calculation thread, if any.
        best_combination (tuple): The best combination of reaction functions found so far.
        best_mse (float): The best (lowest) mean squared error found so far.
        strategy (BestResultStrategy): The current strategy for processing the best results.
    """

    new_best_result = pyqtSignal(dict)

    def __init__(self, signals):
        super().__init__(actor_name="calculations", signals=signals)
        self.thread: Optional[CalculationThread] = None
        self.best_combination: Optional[tuple] = None
        self.best_mse: float = float("inf")
        self.new_best_result.connect(self.handle_new_best_result)
        self.mse_history = []
        self.calculation_active = False

        self.deconvolution_strategy = DeconvolutionStrategy(self)
        self.model_based_calculation_strategy = ModelBasedCalculationStrategy(self)
        self.strategy: Optional[BestResultStrategy] = None

    def set_strategy(self, strategy_type: str):
        """
        Sets the current strategy for processing the best results.

        Args:
            strategy_type (str): for now ('deconvolution' or 'model_based_calculation').
        """
        if strategy_type == "deconvolution":
            self.strategy = self.deconvolution_strategy
            logger.debug("Deconvolution strategy set.")
        elif strategy_type == "model_based_calculation":
            self.strategy = self.model_based_calculation_strategy
            logger.debug("Model calculation strategy set.")
        else:
            raise ValueError(f"Unknown strategy type: {strategy_type}")

    def start_calculation_thread(self, func: Callable, *args, **kwargs) -> None:
        self.calculation_active = True
        self.thread = CalculationThread(func, *args, **kwargs)
        self.thread.result_ready.connect(self._calculation_finished)
        self.thread.start()

    @pyqtSlot(dict)
    def process_request(self, params: dict):
        operation = params.get("operation")
        response = params.copy()
        if operation == "stop_calculation":
            response["data"] = self.stop_calculation()

        response["target"], response["actor"] = response["actor"], response["target"]
        self.signals.response_signal.emit(response)

    def stop_calculation(self):
        if self.thread and self.thread.isRunning():
            logger.info("Stopping current calculation...")
            self.calculation_active = False
            self.strategy = None
            self.thread.requestInterruption()
            return True
        return False

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
                self.best_mse = float("inf")
                self.best_combination = None
            else:
                logger.info("Calculation finished with a non-OptimizeResult object.")
                console.log(f"Calculation completed successfully. Result: {result}")

        except ValueError as e:
            logger.error(f"Error processing the result: {e}")
            console.log("An error occurred while processing the calculation result. Check logs for details.")

        self.calculation_active = False
        self.strategy = None
        self.best_mse = float("inf")
        self.best_combination = None
        self.mse_history = []
        self.handle_request_cycle("main_window", "calculation_finished")

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

            target_function = self.generate_deconvolution_target_function(
                reaction_variables, reaction_combinations, experimental_data
            )

            if deconvolution_method == "differential_evolution":
                logger.info("Starting differential evolution optimization.")
                self.set_strategy("deconvolution")
                self.start_differential_evolution(
                    bounds=bounds, target_function=target_function, **deconvolution_parameters
                )
            else:
                logger.error(f"Unknown deconvolution method: {deconvolution_method}")
                console.log("Error: Unknown deconvolution method requested. Check logs.")

        except Exception as e:
            logger.error(f"Error preparing and starting optimization: {e}")
            console.log("Error preparing and starting optimization. Check logs for details.")

    @pyqtSlot(dict)
    def run_model_based_calculation(self, params: dict):
        """
        Prepare and execute the model calculation process.

        Args:
            params (dict): Parameters for model calculation.
        """
        logger.debug(f"run_model_based_calculation called with response: {params}")

        try:
            target_function = self.generate_model_based_target_function(params)

            bounds = params.get("bounds", [])
            optimization_parameters = params.get("optimization_parameters", {})

            logger.info("Starting model based calculation optimization.")
            self.set_strategy("model_based_calculation")
            self.start_differential_evolution(bounds=bounds, target_function=target_function, **optimization_parameters)

        except Exception as e:
            logger.error(f"Error preparing and starting model calculation: {e}")
            console.log("Error preparing and starting model calculation. Check logs for details.")

    def generate_model_based_target_function(self, params):
        pass

    def generate_deconvolution_target_function(
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
            if not self.calculation_active:
                return float("inf")

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

    @pyqtSlot(dict)
    def handle_new_best_result(self, result: dict):
        if self.strategy:
            self.strategy.handle(result)
        else:
            logger.warning("No strategy set. Best result will not be handled.")
