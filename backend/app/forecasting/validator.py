import re
import logging
from typing import List, Tuple
from app.forecasting.schemas import CashForecastResult

logger = logging.getLogger("forecast_validator")

NUMERIC_PATTERN = re.compile(r"\b\d+(?:\.\d+)?\b")
ISO_DATE_PATTERN = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")


def validate_forecast_explanation(explanation: str, forecast_result: CashForecastResult) -> Tuple[bool, List[str]]:
    """Deterministically validates that numeric claims in the explanation match authoritative forecast values."""
    errors = []
    if not explanation or not explanation.strip():
        return (True, [])

    explanation_sans_dates = ISO_DATE_PATTERN.sub("", explanation)

    # Gather all valid numbers from forecast_result
    valid_numbers = set()
    
    # Summary values
    for val in [
        forecast_result.historical.inflow, forecast_result.historical.outflow, forecast_result.historical.net,
        forecast_result.forecast.inflow, forecast_result.forecast.outflow, forecast_result.forecast.net,
        forecast_result.confidence, forecast_result.lookback_days, forecast_result.horizon_days,
        forecast_result.uncertainty.std_dev, forecast_result.uncertainty.margin_of_error,
        forecast_result.data_quality.score
    ]:
        try:
            num = float(val)
            abs_num = abs(num)
            valid_numbers.add(round(num, 2))
            valid_numbers.add(round(abs_num, 2))
            valid_numbers.add(int(abs_num))
        except (ValueError, TypeError):
            pass

    # Daily values
    for d in forecast_result.daily_forecasts:
        for val in [d.expected_inflow, d.expected_outflow, d.expected_net, d.lower_bound, d.upper_bound]:
            try:
                num = float(val)
                abs_num = abs(num)
                valid_numbers.add(round(num, 2))
                valid_numbers.add(round(abs_num, 2))
                valid_numbers.add(int(abs_num))
            except (ValueError, TypeError):
                pass

    found_numbers = NUMERIC_PATTERN.findall(explanation_sans_dates)
    for num_str in found_numbers:
        try:
            num_val = float(num_str)
            # Skip small integers (0..3) or years (2020..2035)
            if (num_val in (0, 1, 2, 3) and "." not in num_str) or (2020 <= num_val <= 2035 and "." not in num_str):
                continue

            rounded_val = round(num_val, 2)
            int_val = int(num_val)

            is_valid = False
            for vn in valid_numbers:
                if abs(vn - num_val) < 0.05 or vn == rounded_val or vn == int_val:
                    is_valid = True
                    break

            if valid_numbers and not is_valid:
                errors.append(f"Forecast Grounding Error: Explanation claims unverified numeric value '{num_str}'.")
        except ValueError:
            pass

    return (len(errors) == 0, errors)
