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
        return self.params.get("calculation_settings", {}).get("method", "differential_evolution")

    def get_bounds(self) -> list[tuple]:
        """
        Формирует список ограничений для параметров оптимизации.
        Параметры для каждой реакции задаются в следующем порядке:
          1. logA (степень десяти)
          2. Ea (энергия активации)
          3. n (экспонента)
          4. вклад (contribution)
        """
        scheme = self.params.get("reaction_scheme")
        if not scheme:
            raise ValueError("No 'reaction_scheme' provided for ModelBasedScenario.")
        reactions = scheme.get("reactions")
        if not reactions:
            raise ValueError("No 'reactions' in reaction_scheme.")

        bounds = []
        # Ограничения для logA (если не заданы – используются значения по умолчанию)
        for reaction in reactions:
            logA_min = reaction.get("log_A_min", 0)
            logA_max = reaction.get("log_A_max", 10)
            bounds.append((logA_min, logA_max))
        # Ограничения для Ea
        for reaction in reactions:
            Ea_min = reaction.get("Ea_min", 40000)
            Ea_max = reaction.get("Ea_max", 200000)
            bounds.append((Ea_min, Ea_max))
        # Ограничения для n (используем фиксированный диапазон)
        for _ in reactions:
            bounds.append((0.1, 4))
        # Ограничения для вкладов
        for reaction in reactions:
            contrib_min = reaction.get("contribution_min", 0)
            contrib_max = reaction.get("contribution_max", 1)
            bounds.append((contrib_min, contrib_max))
        return bounds

    def get_constraints(self):
        """
        Нелинейное ограничение, накладывающее условие, что сумма вкладов (contributions)
        по всем реакциям должна равняться 1.
        """
        scheme = self.params.get("reaction_scheme")
        if not scheme:
            raise ValueError("No 'reaction_scheme' provided for ModelBasedScenario.")
        reactions = scheme.get("reactions")
        if not reactions:
            raise ValueError("No 'reactions' in reaction_scheme.")
        num_reactions = len(reactions)

        def constraint_fun(x):
            return np.sum(x[3 * num_reactions : 4 * num_reactions]) - 1.0

        return NonlinearConstraint(constraint_fun, 0, 0)

    def get_target_function(self) -> Callable:  # noqa: C901
        """
        Формирует целевую функцию в стиле нового кода.
        В ней:
          – параметры X имеют вид: [logA (num_r), Ea (num_r), n (num_r), contributions (num_r)]
          – для каждого значения beta (например, скорость нагрева) проводится интегрирование ОДУ,
            и рассчитывается среднеквадратичная ошибка между экспериментальными и модельными данными.
        """

        from multiprocessing import Manager

        # Получаем схему реакций: ожидается, что схема имеет ключи "components" и "reactions"
        scheme = self.params.get("reaction_scheme")
        if not scheme:
            raise ValueError("No 'reaction_scheme' provided for ModelBasedScenario.")
        reactions = scheme.get("reactions")
        if not reactions:
            raise ValueError("No 'reactions' in reaction_scheme.")
        components = scheme.get("components")
        if not components:
            raise ValueError("No 'components' in reaction_scheme.")

        # Список видов (например, ['A', 'B', ...])
        species_list = [comp["id"] for comp in components]
        # Список пар реакций (например, [('A', 'B'), ...])
        reaction_pairs = [(r["from"], r["to"]) for r in reactions]
        num_species = len(species_list)
        num_reactions = len(reaction_pairs)

        # Получаем экспериментальные данные (pandas DataFrame)
        experimental_data = self.params.get("experimental_data")
        if experimental_data is None:
            raise ValueError("No 'experimental_data' provided for ModelBasedScenario.")

        # Приводим температуру к Кельвинам (если в данных температура в °C)
        exp_temperature = experimental_data["temperature"].to_numpy() + 273.15

        # Определяем список beta (например, скорости нагрева).
        # Если они заданы в настройках расчёта – используем их,
        # иначе пытаемся извлечь из названий столбцов экспериментальных данных.
        calc_settings = self.params.get("calculation_settings", {})
        betas = calc_settings.get("experimental_masses")
        if not betas:
            betas = [float(col) for col in experimental_data.columns if col != "temperature"]
        else:
            betas = [float(b) for b in betas]

        # Формируем список экспериментальных данных для каждого beta
        all_exp_masses = []
        for beta in betas:
            col_name = str(beta)
            if col_name not in experimental_data.columns:
                col_name = str(int(beta))
            if col_name not in experimental_data.columns:
                raise ValueError(f"Experimental data does not contain column for beta value {beta}")
            exp_mass = experimental_data[col_name].to_numpy()
            all_exp_masses.append(exp_mass)

        # Создаём Manager для обмена значением наилучшей MSE между процессами
        manager = Manager()
        best_mse = manager.Value("d", np.inf)
        lock = manager.Lock()

        # Фабрика ОДУ: на основе части параметров X формирует функцию для ОДУ
        def ode_func_factory(x_params, species_list, reaction_pairs, num_species, num_reactions):
            num_r = num_reactions
            logA = np.array(x_params[0:num_r])
            Ea = np.array(x_params[num_r : 2 * num_r])
            n = np.array(x_params[2 * num_r : 3 * num_r])
            R = 8.314

            from_indices = np.array([species_list.index(frm) for frm, _ in reaction_pairs])
            to_indices = np.array([species_list.index(to_) for _, to_ in reaction_pairs])
            Ai = 10**logA

            def ode_func(T, X, beta):
                dXdt = np.zeros_like(X)
                conc = X[0:num_species]
                beta_SI = beta / 60.0
                ki = (Ai * np.exp(-Ea / (R * T))) / beta_SI
                conc_from = np.maximum(conc[from_indices], 0.0)
                ri = ki * (conc_from**n)
                np.subtract.at(dXdt, from_indices, ri)
                np.add.at(dXdt, to_indices, ri)
                # Записываем скорость реакции в последние num_r элементов вектора X
                dXdt[num_species : num_species + num_r] = ri
                return dXdt

            return ode_func

        # Целевая функция для дифференциальной эволюции (см. новый код)
        def target_function_DE(
            X,
            species_list,
            reaction_pairs,
            num_species,
            num_reactions,
            betas,
            all_exp_masses,
            exp_temperature,
            best_mse,
            lock,
        ):
            # Проверяем ограничение суммы вкладов
            sum_contributions = np.sum(X[3 * num_reactions : 4 * num_reactions])
            if not np.isclose(sum_contributions, 1.0, atol=1e-4):
                return 1e12

            ode_func_local = ode_func_factory(
                X[: 3 * num_reactions], species_list, reaction_pairs, num_species, num_reactions
            )
            total_mse = 0.0

            for i, beta_val in enumerate(betas):
                exp_mass_i = all_exp_masses[i]
                T_array = exp_temperature
                X0 = np.zeros(num_species + num_reactions)
                X0[0] = 1.0
                try:
                    sol = solve_ivp(
                        lambda T, vec: ode_func_local(T, vec, beta_val),
                        [T_array[0], T_array[-1]],
                        X0,
                        t_eval=T_array,
                        method="RK45",
                    )
                    if not sol.success:
                        return 1e12

                    ints = sol.y[num_species:, :]  # интегралы по реакциям
                    M0 = exp_mass_i[0]
                    Mfin = exp_mass_i[-1]
                    contrib = X[3 * num_reactions : 4 * num_reactions]
                    # Вычисляем взвешенную сумму интегралов по реакциям
                    int_sum = np.sum(contrib[:, np.newaxis] * ints, axis=0)
                    model_mass = M0 - (M0 - Mfin) * int_sum
                    mse_i = np.mean((model_mass - exp_mass_i) ** 2)
                    total_mse += mse_i
                except Exception as e:
                    logger.error(f"Error in ODE integration: {e}")
                    return 1e12

            with lock:
                if total_mse < best_mse.value:
                    best_mse.value = total_mse

            return total_mse

        # Замыкание, возвращающее целевую функцию с нужными параметрами
        def target_func(X: np.ndarray) -> float:
            return target_function_DE(
                X,
                species_list,
                reaction_pairs,
                num_species,
                num_reactions,
                betas,
                all_exp_masses,
                exp_temperature,
                best_mse,
                lock,
            )

        return target_func


SCENARIO_REGISTRY = {
    "deconvolution": DeconvolutionScenario,
    "model_based_calculation": ModelBasedScenario,
}
