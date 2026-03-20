"""
analysis/optimizer.py
PyPortfolioOpt — efficient frontier, Max Sharpe, Min Volatility, Risk Parity.
"""

import numpy as np
import pandas as pd
import streamlit as st
from pypfopt import EfficientFrontier, risk_models, expected_returns, plotting
from pypfopt.discrete_allocation import DiscreteAllocation, get_latest_prices
from data.fetcher import get_multi_history


def run_optimisation(tickers: list, period: str = "2y", rf: float = 0.04,
                     method: str = "max_sharpe", target_return: float = None,
                     target_risk: float = None) -> dict:
    """
    Run mean-variance optimisation.
    method: 'max_sharpe' | 'min_volatility' | 'efficient_return' | 'efficient_risk'
    Returns dict with weights, performance, and covariance matrix.
    """
    closes = get_multi_history(tickers, period=period)
    if closes.empty or len(closes) < 30:
        return {"error": "Insufficient data for optimisation."}

    # Drop any tickers with too many NaNs
    closes = closes.dropna(axis=1, thresh=int(len(closes) * 0.8))
    closes = closes.fillna(method="ffill").dropna()
    tickers_clean = list(closes.columns)

    mu   = expected_returns.mean_historical_return(closes)
    S    = risk_models.sample_cov(closes)

    ef = EfficientFrontier(mu, S)
    ef.add_constraint(lambda w: w >= 0)   # long-only

    try:
        if method == "max_sharpe":
            ef.max_sharpe(risk_free_rate=rf)
        elif method == "min_volatility":
            ef.min_volatility()
        elif method == "efficient_return" and target_return is not None:
            ef.efficient_return(target_return=target_return / 100)
        elif method == "efficient_risk" and target_risk is not None:
            ef.efficient_risk(target_volatility=target_risk / 100)
        else:
            ef.max_sharpe(risk_free_rate=rf)
    except Exception as e:
        return {"error": str(e)}

    weights_raw = ef.clean_weights()
    perf = ef.portfolio_performance(verbose=False, risk_free_rate=rf)

    return {
        "tickers":        tickers_clean,
        "weights":        dict(weights_raw),
        "exp_return":     round(perf[0] * 100, 2),
        "exp_volatility": round(perf[1] * 100, 2),
        "sharpe":         round(perf[2], 3),
        "mu":             mu,
        "S":              S,
        "closes":         closes,
    }


def efficient_frontier_curve(mu, S, rf: float = 0.04, n_points: int = 60) -> pd.DataFrame:
    """Generate points along the efficient frontier for plotting."""
    returns_range = np.linspace(float(mu.min()), float(mu.max()), n_points)
    vols, rets = [], []
    for r in returns_range:
        try:
            ef = EfficientFrontier(mu, S)
            ef.add_constraint(lambda w: w >= 0)
            ef.efficient_return(target_return=r)
            perf = ef.portfolio_performance(verbose=False, risk_free_rate=rf)
            vols.append(perf[1] * 100)
            rets.append(perf[0] * 100)
        except Exception:
            continue
    return pd.DataFrame({"volatility": vols, "return": rets})


def discrete_allocation(weights: dict, tickers: list, closes: pd.DataFrame,
                        portfolio_value: float = 10_000) -> dict:
    """Convert fractional weights to actual share counts given a portfolio size."""
    latest = get_latest_prices(closes)
    da = DiscreteAllocation(weights, latest, total_portfolio_value=portfolio_value)
    allocation, leftover = da.greedy_portfolio()
    return {"allocation": allocation, "leftover": round(leftover, 2)}


def correlation_matrix(tickers: list, period: str = "1y") -> pd.DataFrame:
    closes = get_multi_history(tickers, period=period)
    if closes.empty:
        return pd.DataFrame()
    return closes.pct_change().dropna().corr().round(3)
