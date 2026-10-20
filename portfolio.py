"""Risk and return calculations for Meridian's simple portfolio baselines."""

from math import sqrt

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
