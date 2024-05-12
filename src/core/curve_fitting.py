import numpy as np


class CurveFitting:
    @staticmethod
    def gaussian(x, h, z, w) -> np.ndarray:
        return h * np.exp(-((x - z) ** 2) / (2 * w ** 2))

    @staticmethod
    def fraser_suzuki(x, h, z, w, a3) -> np.ndarray:
        with np.errstate(divide='ignore', invalid='ignore'):
            result = h * np.exp(-np.log(2)*((np.log(1+2*a3*((x-z)/w))/a3)**2))
        result = np.nan_to_num(result, nan=0)
        return result

    @staticmethod
    def asymmetric_double_sigmoid(x, h, z, w, s1, s2) -> np.ndarray:
        safe_x = np.clip(x, -709, 709)
        exp_arg = -((safe_x - z + w/2) / s1)
        clipped_exp_arg = np.clip(exp_arg, -709, 709)
        term1 = 1 / (1 + np.exp(clipped_exp_arg))
        inner_term = 1 / (1 + np.exp(-((safe_x - z - w/2) / s2)))
        term2 = 1 - inner_term
        return h * term1 * term2
