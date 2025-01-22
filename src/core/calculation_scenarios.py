from typing import Callable, Dict

import numpy as np
from scipy.integrate import solve_ivp
from scipy.optimize import NonlinearConstraint

from src.core.curve_fitting import CurveFitting as cft
from src.core.logger_config import logger


class BaseCalculationScenario:
    def __init__(self, params: Dict, calculations):
        self.params = params
        self.calculations = calculations

    def get_bounds(self) -> list[tuple]:
        raise NotImplementedError

    def get_target_function(self) -> Callable:
        raise NotImplementedError

    def get_optimization_method(self) -> str:
        return "differential_evolution"

    def get_result_strategy_type(self) -> str:
        raise NotImplementedError


class DeconvolutionScenario(BaseCalculationScenario):
    def get_bounds(self) -> list[tuple]:
        return self.params["bounds"]

    def get_optimization_method(self) -> str:
        deconv_settings = self.params.get("deconvolution_settings", {})
        return deconv_settings.pop("method", "differential_evolution")

    def get_result_strategy_type(self) -> str:
        return "deconvolution"

    def get_target_function(self) -> Callable:
        reaction_variables = self.params["reaction_variables"]
        reaction_combinations = self.params["reaction_combinations"]
        experimental_data = self.params["experimental_data"]

        def target_function(params_array: np.ndarray) -> float:
            if not self.calculations.calculation_active:
                return float("inf")

            best_mse = float("inf")
            best_combination = None

            for combination in reaction_combinations:
                cumulative_function = np.zeros(len(experimental_data["temperature"]))

                param_idx_local = 0

                for (reaction, coeffs), func in zip(reaction_variables.items(), combination):
                    coeff_count = len(coeffs)
                    func_params = params_array[param_idx_local : param_idx_local + coeff_count]
                    param_idx_local += coeff_count

                    x = experimental_data["temperature"]

                    # Для всех функций первые 3 params: h, z, w
                    if len(func_params) < 3:
                        raise ValueError("Not enough parameters for the function.")
                    h, z, w = func_params[0:3]

                    if func == "gauss":
                        reaction_values = cft.gaussian(x, h, z, w)
                    elif func == "fraser":
                        fr = func_params[3]  # fraser_suzuki
                        reaction_values = cft.fraser_suzuki(x, h, z, w, fr)
                    elif func == "ads":
                        ads1 = func_params[3]
                        ads2 = func_params[4]
                        reaction_values = cft.asymmetric_double_sigmoid(x, h, z, w, ads1, ads2)
                    else:
                        logger.warning(f"Unknown function type: {func}")
                        reaction_values = 0

                    cumulative_function += reaction_values

                y_true = experimental_data.iloc[:, 1].to_numpy()
                mse = np.mean((y_true - cumulative_function) ** 2)
                if mse < best_mse:
                    best_mse = mse
                    best_combination = combination

                    self.calculations.new_best_result.emit(
                        {"best_mse": best_mse, "best_combination": best_combination, "params": params_array}
                    )

            return best_mse

        return target_function


class ModelBasedScenario(BaseCalculationScenario):
    def get_result_strategy_type(self) -> str:
        return "model_based_calculation"

    def get_optimization_method(self) -> str:
        return self.params.get("model_based_settings", {}).get("method", "differential_evolution")

    def get_bounds(self) -> list[tuple]:
        scheme = self.params.get("scheme")
        if not scheme:
            raise ValueError("No 'scheme' provided for ModelBasedScenario.")

        # Генерация системы ОДУ для определения количества реакций
        ode_system = self._generate_ode_system(scheme)
        reaction_pairs = self._extract_reactions_from_ode_system(ode_system)
        num_reactions = len(reaction_pairs)

        # Извлечение Beta из series_df
        series_df = self.params.get("series_df")
        beta_series = [float(beta) for beta in series_df.columns if beta != "temperature"]
        num_experiments = len(beta_series)  # noqa: F841

        # Количество Contributions равно количеству реакций
        num_contributions = num_reactions

        # Границы для A, Ea, n
        bounds = (
            [(0.01, 15.0) for _ in range(num_reactions)]  # A
            + [(40000.0, 200000.0) for _ in range(num_reactions)]  # Ea
            + [(0.01, 4.0) for _ in range(num_reactions)]  # n
        )

        # Границы для Contributions (от 0 до 1)
        bounds += [(0.0, 1.0) for _ in range(num_contributions)]

        return bounds

    def get_constraints(self):
        scheme = self.params.get("scheme")
        ode_system = self._generate_ode_system(scheme)
        reaction_pairs = self._extract_reactions_from_ode_system(ode_system)
        num_reactions = len(reaction_pairs)
        num_contributions = num_reactions

        # Индексы для Contributions в параметрах
        contributions_start = 3 * num_reactions
        contributions_end = contributions_start + num_contributions

        # Функция для ограничения суммы Contributions
        def constraint_func(x):
            return np.sum(x[contributions_start:contributions_end]) - 1

        return NonlinearConstraint(constraint_func, 0, 0)

    def get_target_function(self) -> Callable:
        scheme = self.params.get("scheme")
        series_df = self.params.get("series_df")

        if not scheme or series_df is None:
            raise ValueError("Missing 'scheme' or 'series_df' in params")

        # Генерация системы ОДУ и извлечение реакций
        ode_system = self._generate_ode_system(scheme)
        reaction_pairs = self._extract_reactions_from_ode_system(ode_system)
        num_reactions = len(reaction_pairs)
        species = list(ode_system.keys())
        num_species = len(species)

        # Извлечение Beta из series_df
        beta_series = [float(beta) for beta in series_df.columns if beta != "temperature"]
        # num_experiments = len(beta_series)

        # Индексы реакций
        # reaction_indices = {pair: idx for idx, pair in enumerate(reaction_pairs)}

        def target_function(parameters: np.ndarray) -> float:
            try:
                # Извлечение параметров
                A = 10 ** parameters[:num_reactions]
                Ea = parameters[num_reactions : 2 * num_reactions]
                n = parameters[2 * num_reactions : 3 * num_reactions]
                Contributions = parameters[3 * num_reactions : 4 * num_reactions]

                R = 8.3144598

                # Проверка суммы Contributions
                if not np.isclose(np.sum(Contributions), 1.0):
                    return np.inf

                total_mse = 0.0

                for i, beta in enumerate(beta_series):
                    temperature = series_df["temperature"].to_numpy()
                    experimental_data = series_df.iloc[:, i + 1].to_numpy()

                    # Расчёт констант скорости с учётом Beta
                    k = A * np.exp(-Ea / (R * temperature)) / (beta / 60)  # Перевод Beta в секунды

                    # Задание начальных концентраций
                    X0 = np.zeros(num_species)
                    X0[0] = 1.0  # Начальная концентрация вида A

                    # Инициализация массива для хранения интегралов d(r)/dt
                    integral_dr_dt = np.zeros(num_reactions)

                    # Определение функции ОДУ
                    def ode_func(t, X):
                        # Интерполяция текущей температуры
                        idx = np.argmin(np.abs(temperature - t))
                        current_k = k[idx]

                        dXdt = np.zeros(num_species)

                        # Построение системы уравнений на основе схемы реакций
                        for r_idx, (from_s, to_s) in enumerate(reaction_pairs):
                            # Найти индексы реагентов и продуктов
                            from_idx = species.index(from_s)
                            to_idx = species.index(to_s)

                            # Рассчитать скорость реакции
                            rate = current_k[r_idx] * X[from_idx] ** n[r_idx]

                            # Изменение концентраций
                            dXdt[from_idx] -= rate
                            dXdt[to_idx] += rate

                            # Накопление интеграла d(r)/dt
                            # Предполагаем равномерное распределение времени между точками
                            dt = temperature[1] - temperature[0]  # Предположим равномерный шаг
                            integral_dr_dt[r_idx] += rate * dt

                        return dXdt

                    # Решение ОДУ
                    sol = solve_ivp(ode_func, [temperature[0], temperature[-1]], X0, t_eval=temperature, method="RK45")

                    if not sol.success:
                        return np.inf

                    # Расчёт теоретической массы
                    mass_change = np.dot(Contributions, integral_dr_dt)
                    initial_mass = 100.0  # Предположим начальную массу
                    mass_theoretical = initial_mass - mass_change

                    # Расчёт MSE
                    mse = np.mean((mass_theoretical - experimental_data) ** 2)
                    total_mse += mse

                return total_mse

            except Exception as e:
                logger.error(f"Error in model-based target function: {e}")
                return np.inf

        return target_function

    def _generate_ode_system(self, scheme: dict) -> dict:
        nodes = [node["id"] for node in scheme["nodes"]]

        outgoing = {node: [] for node in nodes}
        incoming = {node: [] for node in nodes}

        for edge in scheme["edges"]:
            source = edge["from"]
            target = edge["to"]
            outgoing[source].append(target)
            incoming[target].append(source)

        equations = {}
        for node in nodes:
            consumption_terms = [f"k_{node}_{to} * [{node}]" for to in outgoing[node]]
            formation_terms = [f"k_{source}_to_{node} * [{source}]" for source in incoming[node]]

            formation = " + ".join(formation_terms) if formation_terms else "0"
            consumption = " + ".join(consumption_terms) if consumption_terms else "0"
            equation = f"{formation} - ({consumption})"
            equations[node] = equation

        logger.debug(f"Generated ODE system: {equations}")
        return equations

    def _extract_reactions_from_ode_system(self, ode_system: dict) -> list[tuple[str, str]]:
        reaction_pairs = []
        for species_name, expr in ode_system.items():
            tokens = expr.replace("(", "").replace(")", "").replace("-", "+").split("+")
            for token in tokens:
                token = token.strip()
                if "k_" in token:
                    parts = token.split("*")[0].strip().split("_")
                    if len(parts) >= 3:
                        _, from_s, to_s = parts[:3]
                        reaction_pairs.append((from_s, to_s))
        return list(set(reaction_pairs))


SCENARIO_REGISTRY = {
    "deconvolution": DeconvolutionScenario,
    "model_based_calculation": ModelBasedScenario,
}
