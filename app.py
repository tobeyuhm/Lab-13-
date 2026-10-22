"""Streamlit interface for the portfolio stability learning demonstration."""

from copy import deepcopy
import importlib

import streamlit as st

import portfolio


def format_result(result, names):
    """Render an optimization result, or its honest infeasibility message."""
    if result is None:
        st.warning("No mix meets the objective.")
        return
    st.dataframe(
        {"Asset": names, "Weight": [f"{result['weights'][name] * 100:.0f}%" for name in names]},
        hide_index=True,
        use_container_width=True,
    )
    st.write(f"Expected return: **{result['return'] * 100:.2f}%**")
    st.write(f"Volatility: **{result['volatility'] * 100:.2f}%**")
    st.write(f"Reserve-eligible weight: **{result['reserve_weight'] * 100:.2f}%**")


def largest_weight_change(left, right):
    """Return the largest absolute allocation change in percentage points."""
    if left is None or right is None:
        return None
    return max(abs(left["weights"][name] - right["weights"][name]) * 100 for name in left["weights"])


def main():
    # Reloading makes a saved change in portfolio.py (for example, a correlation)
    # visible on the next Streamlit rerun.
    importlib.reload(portfolio)

    st.set_page_config(page_title="Portfolio Stability Decision", layout="wide")
    st.title("Portfolio Stability Decision")
    st.caption("Built with AI help, a learning demonstration, not investment advice.")

    with st.sidebar:
        st.header("Mandate controls")
        objective = st.number_input("Objective expected return (%)", value=6.5, step=0.1) / 100
        reserve_minimum = st.number_input("Reserve minimum (%)", value=3.0, step=0.1) / 100
        upload = st.file_uploader("Upload monthly prices.csv", type="csv")
        use_last_36 = st.toggle("Use last 36 monthly returns", value=False)

    try:
        if upload is None:
            loaded_sleeves = deepcopy(portfolio.SLEEVES)
            loaded_correlations = deepcopy(portfolio.CORRELATIONS)
            active_sleeves = deepcopy(loaded_sleeves)
            active_correlations = deepcopy(loaded_correlations)
            data_label = "Meridian inputs"
        else:
            loaded_sleeves, loaded_correlations = portfolio.estimate_from_prices_csv(upload, False)
            active_sleeves, active_correlations = portfolio.estimate_from_prices_csv(upload, use_last_36)
            data_label = "CSV estimates (last 36 monthly returns)" if use_last_36 else "CSV estimates (all monthly returns)"
    except ValueError as error:
        st.error(f"CSV input error: {error}")
        return

    st.subheader(data_label)
    st.caption("Expected returns are historical five-year monthly-price estimates, not forecasts.")
    st.write("Edit an expected-return estimate or select which assets are reserve-eligible.")
    names = list(active_sleeves)
    columns = st.columns(min(3, len(names)))
    for index, name in enumerate(names):
        with columns[index % len(columns)]:
            active_sleeves[name]["return"] = st.number_input(
                f"{name} expected return (%)", value=active_sleeves[name]["return"] * 100,
                step=0.1, key=f"return_{name}",
            ) / 100
            active_sleeves[name]["reserve_eligible"] = st.checkbox(
                f"{name} is reserve-eligible", value=active_sleeves[name]["reserve_eligible"],
                key=f"reserve_{name}",
            )

    # The reserve rule is a mandate choice, not an estimated market input. Apply
    # the selected eligibility flags to the all-month comparison as well.
    for name in names:
        loaded_sleeves[name]["reserve_eligible"] = active_sleeves[name]["reserve_eligible"]

    # The comparison remains the as-loaded inputs: Meridian, or the uploaded CSV on all months.
    baseline = portfolio.lowest_risk_mix(
        loaded_sleeves, loaded_correlations, objective, reserve_minimum
    )
    current = portfolio.lowest_risk_mix(
        active_sleeves, active_correlations, objective, reserve_minimum
    )

    current_column, baseline_column = st.columns(2)
    with current_column:
        st.subheader("Lowest-risk mix with current controls")
        format_result(current, names)
    with baseline_column:
        st.subheader("Answer for inputs as loaded")
        format_result(baseline, list(loaded_sleeves))

    change = largest_weight_change(current, baseline)
    if change is None:
        st.info("Largest weight change is unavailable because one comparison mix is infeasible.")
    else:
        st.success(f"Largest weight change: {change:.0f} percentage points.")


if __name__ == "__main__":
    main()
