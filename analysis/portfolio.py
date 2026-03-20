"""
analysis/portfolio.py
Pandas-powered portfolio analytics: P&L, returns, drawdown, Sharpe, VaR.
"""
 
import pandas as pd
import numpy as np
from data.fetcher import get_multi_history, get_quote
 
 
def build_portfolio_df(positions: dict) -> pd.DataFrame:
    """
    Build portfolio DataFrame.
    Cost Basis and Avg Cost come ONLY from config — never from API.
    Live price, P&L, and day change come from yfinance.
    """
    rows = []
    for ticker, pos in positions.items():
        qty      = pos["qty"]
        avg_cost = pos["avg_cost"]
        # Cost basis is ALWAYS qty * avg_cost from config — never changes
        cost_val = round(qty * avg_cost, 2)
 
        q = get_quote(ticker)
        if not q or not q.get("price"):
            # Still show position even if price unavailable
            rows.append({
                "Ticker":      ticker,
                "Name":        ticker,
                "Qty":         qty,
                "Avg Cost":    avg_cost,
                "Last Price":  0,
                "Mkt Value":   0,
                "Cost Basis":  cost_val,
                "P&L ($)":     0,
                "P&L (%)":     0,
                "Day P&L ($)": 0,
                "Chg (%)":     0,
                "Beta":        None,
                "Sector":      "—",
            })
            continue
 
        price    = float(q["price"])
        mkt_val  = round(qty * price, 2)
        pnl      = round(mkt_val - cost_val, 2)
        pnl_pct  = round((pnl / cost_val * 100) if cost_val else 0, 2)
        day_pnl  = round(qty * float(q.get("chg", 0)), 2)
 
        rows.append({
            "Ticker":      ticker,
            "Name":        q.get("name", ticker),
            "Qty":         qty,
            "Avg Cost":    avg_cost,
            "Last Price":  price,
            "Mkt Value":   mkt_val,
            "Cost Basis":  cost_val,
            "P&L ($)":     pnl,
            "P&L (%)":     pnl_pct,
            "Day P&L ($)": day_pnl,
            "Chg (%)":     float(q.get("chg_pct", 0)),
            "Beta":        q.get("beta"),
            "Sector":      q.get("sector", "—"),
        })
 
    return pd.DataFrame(rows)
 
 
def portfolio_summary(df: pd.DataFrame) -> dict:
    """Scalar summary stats from the portfolio DataFrame."""
    if df.empty:
        return {}
    total_val  = df["Mkt Value"].sum()
    total_cost = df["Cost Basis"].sum()
    total_pnl  = df["P&L ($)"].sum()
    day_pnl    = df["Day P&L ($)"].sum()
    return {
        "total_value":  round(total_val, 2),
        "total_cost":   round(total_cost, 2),
        "total_pnl":    round(total_pnl, 2),
        "total_pnl_pct": round((total_pnl / total_cost * 100) if total_cost else 0, 2),
        "day_pnl":      round(day_pnl, 2),
        "day_pnl_pct":  round((day_pnl / total_cost * 100) if total_cost else 0, 2),
        "num_positions": len(df),
    }
 
 
def get_portfolio_returns(tickers: list, weights: dict, period: str = "1y") -> pd.Series:
    """
    Weighted daily portfolio returns.
    weights: { "AAPL": 0.4, "TSLA": 0.6, ... } — must sum to 1.
    """
    closes = get_multi_history(tickers, period=period)
    if closes.empty:
        return pd.Series(dtype=float)
    returns = closes.pct_change().dropna()
    w = pd.Series(weights).reindex(returns.columns).fillna(0)
    w = w / w.sum()
    port_returns = returns.dot(w)
    return port_returns
 
 
def compute_metrics(returns: pd.Series, rf: float = 0.04) -> dict:
    """Compute key risk/return metrics from a daily returns series."""
    if returns.empty:
        return {}
 
    ann_factor   = 252
    total_return = (1 + returns).prod() - 1
    ann_return   = (1 + total_return) ** (ann_factor / len(returns)) - 1
    ann_vol      = returns.std() * np.sqrt(ann_factor)
    sharpe       = (ann_return - rf) / ann_vol if ann_vol else 0
 
    cumulative   = (1 + returns).cumprod()
    rolling_max  = cumulative.cummax()
    drawdown     = (cumulative - rolling_max) / rolling_max
    max_dd       = drawdown.min()
 
    var_95  = returns.quantile(0.05)
    cvar_95 = returns[returns <= var_95].mean()
 
    sortino_denom = returns[returns < 0].std() * np.sqrt(ann_factor)
    sortino = (ann_return - rf) / sortino_denom if sortino_denom else 0
 
    calmar = ann_return / abs(max_dd) if max_dd else 0
 
    win_rate = (returns > 0).mean()
 
    return {
        "total_return":  round(total_return * 100, 2),
        "ann_return":    round(ann_return * 100, 2),
        "ann_vol":       round(ann_vol * 100, 2),
        "sharpe":        round(sharpe, 3),
        "sortino":       round(sortino, 3),
        "calmar":        round(calmar, 3),
        "max_drawdown":  round(max_dd * 100, 2),
        "var_95":        round(var_95 * 100, 2),
        "cvar_95":       round(cvar_95 * 100, 2),
        "win_rate":      round(win_rate * 100, 2),
    }
 
 
def drawdown_series(returns: pd.Series) -> pd.Series:
    cumulative  = (1 + returns).cumprod()
    rolling_max = cumulative.cummax()
    return (cumulative - rolling_max) / rolling_max * 100
 
