"""Risk and return calculations for Meridian's simple portfolio baselines."""

import csv
from io import StringIO
from math import sqrt
from pathlib import Path

# Editable inputs. Returns and volatilities are decimals (for example, 3.5% = 0.035).
SLEEVES = {
    "Treasury bills": {"return": 0.035, "volatility": 0.005, "reserve_eligible": True},
    "Treasury 10-year note": {"return": 0.043, "volatility": 0.070, "reserve_eligible": True},
    "Investment-grade bond fund": {"return": 0.050, "volatility": 0.060, "reserve_eligible": False},
    "Global equity index fund": {"return": 0.080, "volatility": 0.160, "reserve_eligible": False},
}

CORRELATIONS = {
    "Treasury bills": {"Treasury bills": 1.00, "Treasury 10-year note": 0.10,
                       "Investment-grade bond fund": 0.05, "Global equity index fund": 0.00},
    "Treasury 10-year note": {"Treasury bills": 0.10, "Treasury 10-year note": 1.00,
                                "Investment-grade bond fund": 0.80, "Global equity index fund": -0.10},
    "Investment-grade bond fund": {"Treasury bills": 0.05, "Treasury 10-year note": 0.80,
                                     "Investment-grade bond fund": 1.00, "Global equity index fund": 0.25},
    "Global equity index fund": {"Treasury bills": 0.00, "Treasury 10-year note": -0.10,
                                   "Investment-grade bond fund": 0.25, "Global equity index fund": 1.00},
}

OBJECTIVE_RETURN = 0.065  # CPI estimate (2.5%) + 4.0%


def validate_correlation_table(sleeves, correlations):
    """Reject a correlation table that is incomplete, out of range, or asymmetric."""
    names = set(sleeves)
    if set(correlations) != names:
        raise ValueError("Correlation table must have one row for every sleeve.")
    for left in names:
        if set(correlations[left]) != names:
            raise ValueError(f"Correlation row for {left} must have every sleeve.")
        for right in names:
            value = correlations[left][right]
            if not -1 <= value <= 1:
                raise ValueError(f"Correlation for {left} and {right} is outside -1 to 1.")
            if value != correlations[right][left]:
                raise ValueError(f"Correlation table is not symmetric for {left} and {right}.")


def covariance_matrix(sleeves, correlations):
    """Build covariance = correlation x volatility x volatility."""
    return {
        left: {
            right: correlations[left][right]
            * sleeves[left]["volatility"] * sleeves[right]["volatility"]
            for right in sleeves
        }
        for left in sleeves
    }


def portfolio_return(weights, sleeves):
    """Calculate the weighted expected return."""
    return sum(weights[name] * sleeves[name]["return"] for name in sleeves)


def portfolio_variance(weights, covariance):
    """Calculate w' C w: every weight pair times its covariance."""
    return sum(
        weights[left] * weights[right] * covariance[left][right]
        for left in weights for right in weights
    )


def portfolio_volatility(weights, covariance):
    """Return the square root of portfolio variance."""
    return sqrt(portfolio_variance(weights, covariance))


def reserve_eligible_weight(weights, sleeves):
    """Add weights in bills and the 10-year note (the reserve-eligible sleeves)."""
    return sum(weights[name] for name in sleeves if sleeves[name]["reserve_eligible"])


def equal_weight_portfolio(sleeves):
    """Give every sleeve the same weight."""
    return {name: 1 / len(sleeves) for name in sleeves}


def inverse_volatility_portfolio(sleeves):
    """Weight sleeves in proportion to 1 divided by their volatility."""
    raw_weights = {name: 1 / details["volatility"] for name, details in sleeves.items()}
    total = sum(raw_weights.values())
    return {name: value / total for name, value in raw_weights.items()}


def lowest_risk_mix(sleeves, correlations, objective, reserve_minimum, step=0.05):
    """Search long-only, whole-portfolio weight mixes and return the lowest-volatility feasible one.

    ``step`` is a decimal weight: 0.05 means five percentage-point increments.
    Returns ``None`` when no mix reaches both the return objective and reserve rule.
    """
    validate_correlation_table(sleeves, correlations)
    if not 0 < step <= 1 or round(1 / step) != 1 / step:
        raise ValueError("Step must divide evenly into 100%.")
    if not 0 <= reserve_minimum <= 1:
        raise ValueError("Reserve minimum must be between 0% and 100%.")

    names = list(sleeves)
    units = round(1 / step)
    covariance = covariance_matrix(sleeves, correlations)
    best = None

    def try_weights(position, remaining, current):
        nonlocal best
        if position == len(names) - 1:
            weights = {**current, names[position]: remaining * step}
            expected = portfolio_return(weights, sleeves)
            reserve_weight = reserve_eligible_weight(weights, sleeves)
            if expected < objective or reserve_weight < reserve_minimum:
                return
            volatility = portfolio_volatility(weights, covariance)
            candidate = {
                "weights": weights,
                "return": expected,
                "volatility": volatility,
                "reserve_weight": reserve_weight,
            }
            if best is None or volatility < best["volatility"]:
                best = candidate
            return

        for weight_units in range(remaining + 1):
            try_weights(position + 1, remaining - weight_units,
                        {**current, names[position]: weight_units * step})

    try_weights(0, units, {})
    return best


def estimate_from_prices_csv(csv_source, last_36_months=False):
    """Estimate annualized returns, volatility, and correlations from monthly price CSV data.

    The CSV must have a date in its first column (oldest month first) and one price
    column for each ticker. Returns are historical estimates: mean monthly return
    times 12 and sample standard deviation times square root of 12.
    """
    if isinstance(csv_source, (str, Path)):
        with Path(csv_source).open(newline="", encoding="utf-8") as file:
            rows = list(csv.reader(file))
    else:
        if hasattr(csv_source, "seek"):
            csv_source.seek(0)
        content = csv_source.read()
        if isinstance(content, bytes):
            content = content.decode("utf-8-sig")
        rows = list(csv.reader(StringIO(content)))
    if len(rows) < 3:
        raise ValueError("The CSV needs a header and at least two monthly prices.")
    headers = rows[0]
    if len(headers) < 2:
        raise ValueError("The CSV needs a date column and at least one ticker column.")
    names = headers[1:]
    if not all(names) or len(set(names)) != len(names):
        raise ValueError("Each ticker column needs a unique header.")

    prices = {name: [] for name in names}
    for row_number, row in enumerate(rows[1:], start=2):
        if len(row) != len(headers):
            raise ValueError(f"Row {row_number} does not have every price column.")
        try:
            values = [float(value) for value in row[1:]]
        except ValueError as error:
            raise ValueError(f"Row {row_number} contains a non-numeric price.") from error
        if any(value <= 0 for value in values):
            raise ValueError(f"Row {row_number} contains a price that is not positive.")
        for name, value in zip(names, values):
            prices[name].append(value)

    monthly = {
        name: [later / earlier - 1 for earlier, later in zip(values, values[1:])]
        for name, values in prices.items()
    }
    if last_36_months:
        monthly = {name: values[-36:] for name, values in monthly.items()}
    observations = len(next(iter(monthly.values())))
    if observations < 2:
        raise ValueError("At least three prices are needed to estimate volatility and correlation.")

    means = {name: sum(values) / observations for name, values in monthly.items()}
    monthly_stdev = {
        name: sqrt(sum((value - means[name]) ** 2 for value in values) / (observations - 1))
        for name, values in monthly.items()
    }
    if any(value == 0 for value in monthly_stdev.values()):
        raise ValueError("Correlation cannot be calculated for a ticker with zero volatility.")

    sleeves = {
        name: {
            "return": means[name] * 12,
            "volatility": monthly_stdev[name] * sqrt(12),
            "reserve_eligible": False,
        }
        for name in names
    }
    correlations = {name: {} for name in names}
    for left_index, left in enumerate(names):
        correlations[left][left] = 1.0
        for right in names[left_index + 1:]:
            correlation = sum(
                (left_value - means[left]) * (right_value - means[right])
                for left_value, right_value in zip(monthly[left], monthly[right])
            ) / ((observations - 1) * monthly_stdev[left] * monthly_stdev[right])
            correlations[left][right] = correlation
            correlations[right][left] = correlation
    return sleeves, correlations


def print_portfolio(name, weights, sleeves, covariance, objective):
    """Print one portfolio's inputs-derived results."""
    weight_text = " / ".join(f"{weights[sleeve] * 100:.1f}" for sleeve in sleeves)
    expected = portfolio_return(weights, sleeves)
    volatility = portfolio_volatility(weights, covariance)
    reserve_weight = reserve_eligible_weight(weights, sleeves)
    meets_objective = "yes" if expected >= objective else "no"
    print(f"\n{name}")
    print(f"Weights (bills / 10-year / IG / equity): {weight_text}")
    print(f"Expected return: {expected * 100:.2f}%")
    print(f"Volatility: {volatility * 100:.2f}%")
    print(f"Reserve-eligible: {reserve_weight * 100:.1f}%")
    print(f"Meets {objective * 100:.1f}% objective? {meets_objective}")


def main():
    validate_correlation_table(SLEEVES, CORRELATIONS)
    covariance = covariance_matrix(SLEEVES, CORRELATIONS)
    portfolios = {
        "Benchmark": {"Treasury bills": 0, "Treasury 10-year note": 0,
                      "Investment-grade bond fund": 0.40, "Global equity index fund": 0.60},
        "Equal weight": equal_weight_portfolio(SLEEVES),
        "Inverse volatility": inverse_volatility_portfolio(SLEEVES),
    }
    for name, weights in portfolios.items():
        print_portfolio(name, weights, SLEEVES, covariance, OBJECTIVE_RETURN)


if __name__ == "__main__":
    try:
        main()
    except ValueError as error:
        print(f"Input error: {error}")
