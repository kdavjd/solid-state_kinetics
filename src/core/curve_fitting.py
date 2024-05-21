import numpy as np


class CurveFitting:
    @staticmethod
    def generate_default_function_data(df):
        x = df['temperature'].copy()
        y_columns = [col for col in df.columns if col != 'temperature']
        if y_columns:
            y = df[y_columns[0]]
            h = 0.3 * y.max()
            z = x.mean()
            w = 0.1 * (x.max() - x.min())

            h_lower, h_upper = h * 0.9, h * 1.1
            w_lower, w_upper = w * 0.9, w * 1.1
            fr, ads1, ads2 = -1, 1, 1

            result_dict = {
                "function": "gauss",
                "x": x.to_numpy(),
                "coeffs": {
                    "h": h,
                    "z": z,
                    "w": w,
                    "fr": fr,
                    "ads1": ads1,
                    "ads2": ads2
                },
                "upper_bound_coeffs": {
                    "h": h_upper,
                    "z": z + 5,
                    "w": w_upper,
                    "fr": fr,
                    "ads1": ads1,
                    "ads2": ads2
                },
                "lower_bound_coeffs": {
                    "h": h_lower,
                    "z": z - 5,
                    "w": w_lower,
                    "fr": fr,
                    "ads1": ads1,
                    "ads2": ads2
                }
            }
            return result_dict
        return {}

    @staticmethod
    def gaussian(x, h, z, w) -> np.ndarray:
        return h * np.exp(-((x - z) ** 2) / (2 * w ** 2))

    @staticmethod
    def fraser_suzuki(x, h, z, w, fs) -> np.ndarray:
        with np.errstate(divide='ignore', invalid='ignore'):
            result = h * np.exp(-np.log(2)*((np.log(1+2*fs*((x-z)/w))/fs)**2))
        result = np.nan_to_num(result, nan=0)
        return result

    @staticmethod
    def asymmetric_double_sigmoid(x, h, z, w, ads1, ads2) -> np.ndarray:
        safe_x = np.clip(x, -709, 709)
        exp_arg = -((safe_x - z + w/2) / ads1)
        clipped_exp_arg = np.clip(exp_arg, -709, 709)
        term1 = 1 / (1 + np.exp(clipped_exp_arg))
        inner_term = 1 / (1 + np.exp(-((safe_x - z - w/2) / ads2)))
        term2 = 1 - inner_term
        return h * term1 * term2
