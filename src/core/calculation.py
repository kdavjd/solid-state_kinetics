from typing import Callable, Optional

from core.base_signals import BaseSlots
from core.calculation_results_strategies import (
    BestResultStrategy,
    DeconvolutionStrategy,
    ModelBasedCalculationStrategy,
)
from PyQt6.QtCore import pyqtSignal, pyqtSlot
from scipy.optimize import OptimizeResult, differential_evolution

from src.core.calculation_scenarios import SCENARIO_REGISTRY
from src.core.calculation_thread import CalculationThread
from src.core.logger_config import logger
from src.core.logger_console import LoggerConsole as console


class Calculations(BaseSlots):
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
        self.result_strategy: Optional[BestResultStrategy] = None

    def set_result_strategy(self, strategy_type: str):
        if strategy_type == "deconvolution":
            self.result_strategy = self.deconvolution_strategy
        elif strategy_type == "model_based_calculation":
            self.result_strategy = self.model_based_calculation_strategy
        else:
            raise ValueError(f"Unknown strategy type: {strategy_type}")

    def start_calculation_thread(self, func: Callable, *args, **kwargs) -> None:
        self.calculation_active = True
        self.thread = CalculationThread(func, *args, **kwargs)
        self.thread.result_ready.connect(self._calculation_finished)
        self.thread.start()

    def stop_calculation(self):
        if self.thread and self.thread.isRunning():
            logger.info("Stopping current calculation...")
            self.calculation_active = False
            self.result_strategy = None
            self.thread.requestInterruption()
            return True
        return False

    @pyqtSlot(dict)
    def process_request(self, params: dict):
        operation = params.get("operation")
        response = params.copy()
        if operation == "stop_calculation":
            response["data"] = self.stop_calculation()

        response["target"], response["actor"] = response["actor"], response["target"]
        self.signals.response_signal.emit(response)

    @pyqtSlot(dict)
    def run_calculation_scenario(self, params: dict):
        scenario_key = params.get("calculation_scenario")
        if not scenario_key:
            logger.error("No 'calculation_scenario' provided in params.")
            return

        scenario_cls = SCENARIO_REGISTRY.get(scenario_key)
        if not scenario_cls:
            logger.error(f"Unknown calculation scenario: {scenario_key}")
            return

        scenario_instance = scenario_cls(params, self)

        try:
            bounds = scenario_instance.get_bounds()
            target_function = scenario_instance.get_target_function()
            optimization_method = scenario_instance.get_optimization_method()
            strategy_type = scenario_instance.get_result_strategy_type()

            self.set_result_strategy(strategy_type)

            if optimization_method == "differential_evolution":
                calc_params = params.get("calculation_settings", {}).get("method_parameters", {}).copy()

                self.start_differential_evolution(bounds=bounds, target_function=target_function, **calc_params)
            else:
                logger.error(f"Unsupported optimization method: {optimization_method}")

        except Exception as e:
            logger.error(f"Error setting up scenario '{scenario_key}': {e}")
            console.log(f"Error setting up scenario '{scenario_key}': {e}")

    def start_differential_evolution(self, bounds, target_function, **kwargs):
        self.start_calculation_thread(
            differential_evolution,
            target_function,
            bounds=bounds,
            **kwargs,
        )

    @pyqtSlot(object)
    def _calculation_finished(self, result):
        try:
            if isinstance(result, OptimizeResult):
                x = result.x
                fun = result.fun
                logger.info(f"Calculation completed. Optimal parameters: {x}, fun={fun}")
                console.log(f"Calculation completed. Optimal parameters: {x}, fun={fun}")
                self.best_mse = float("inf")
                self.best_combination = None
            else:
                logger.info("Calculation finished with a non-OptimizeResult object.")
                console.log(f"Calculation result: {result}")

        except ValueError as e:
            logger.error(f"Error processing the result: {e}")
            console.log("An error occurred while processing the result. Check logs for details.")

        self.calculation_active = False
        self.result_strategy = None
        self.best_mse = float("inf")
        self.best_combination = None
        self.mse_history = []
        self.handle_request_cycle("main_window", "calculation_finished")

    @pyqtSlot(dict)
    def handle_new_best_result(self, result: dict):
        if self.result_strategy:
            self.result_strategy.handle(result)
        else:
            logger.warning("No strategy set. Best result will not be handled.")
