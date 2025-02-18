import datetime
from abc import ABC, abstractmethod
from typing import Dict

from src.core.app_settings import OperationType
from src.core.logger_config import logger
from src.core.logger_console import LoggerConsole as console


class BestResultStrategy(ABC):
    @abstractmethod
    def handle(self, result: Dict):
        pass


class DeconvolutionStrategy(BestResultStrategy):
    def __init__(self, calculation_instance):
        self.calculation = calculation_instance

    def handle(self, result: Dict):  # noqa: C901
        best_mse = result.get("best_mse")
        best_combination = result.get("best_combination")
        params = result.get("params")

        if best_mse < self.calculation.best_mse:
            self.calculation.best_mse = best_mse
            self.calculation.best_combination = best_combination
            self.calculation.mse_history.append((datetime.datetime.now(), best_mse))
            logger.info("A new best MSE has been found.")

            self.calculation.handle_request_cycle(
                "main_window", OperationType.PLOT_MSE_LINE, mse_data=self.calculation.mse_history
            )

            def reaction_param_count(func_type: str) -> int:
                if func_type == "gauss":
                    return 3
                elif func_type == "fraser":
                    return 4
                elif func_type == "ads":
                    return 5
                else:
                    return 3  # Default

            idx = 0
            parameters_yaml = "parameters:\n"
            for i, func_type in enumerate(best_combination, start=1):
                count = reaction_param_count(func_type)
                reaction_params = params[idx : idx + count]
                idx += count

                param_dict = {
                    "h": None,
                    "z": None,
                    "w": None,
                    "fr": None,
                    "ads1": None,
                    "ads2": None,
                }

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
                    continue

                parameters_yaml += f"  r{i}:\n"
                for key, value in param_dict.items():
                    val_str = "null" if value is None else f"{value:.4f}"
                    parameters_yaml += f"    {key}: {val_str}\n"

            console.log("\nNew best result found:")
            console.log(f"\nBest MSE: {best_mse:.4f}")
            console.log(f"\nReaction combination: {best_combination}")
            console.log(parameters_yaml.rstrip())

            file_name = self.calculation.handle_request_cycle("main_window", OperationType.GET_FILE_NAME)
            self.calculation.handle_request_cycle(
                "calculations_data_operations",
                OperationType.UPDATE_REACTIONS_PARAMS,
                path_keys=[file_name],
                best_combination=best_combination,
                reactions_params=params,
            )


class ModelBasedCalculationStrategy(BestResultStrategy):
    def __init__(self, calculation_instance):
        self.calculation = calculation_instance

    def handle(self, result: Dict):
        best_mse = result.get("best_mse")
        best_combination = result.get("best_combination")
        params = result.get("params")

        if best_mse < self.calculation.best_mse:
            self.calculation.best_mse = best_mse
            self.calculation.best_combination = best_combination
            self.calculation.mse_history.append((datetime.datetime.now(), best_mse))
            logger.info("A new best MSE has been found in model calculation.")

            self.calculation.handle_request_cycle(
                "main_window", OperationType.PLOT_MSE_LINE, mse_data=self.calculation.mse_history
            )

            console.log("\nNew best result found in model calculation:")
            console.log(f"Best MSE: {best_mse:.4f}")
            console.log(f"Best combination: {best_combination}")
            console.log(f"Parameters: {params}")
