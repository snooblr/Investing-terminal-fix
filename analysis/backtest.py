"""
analysis/backtest.py
vectorbt-powered backtesting: SMA crossover, RSI mean-reversion, Buy & Hold.
All strategies return a vbt.Portfolio object for rich stats + drawdown access.
"""

import numpy as np
import pandas as pd
import vectorbt as vbt
import streamlit as st
from data.fetcher import get_history


# ── Strategy: Buy & Hold ──────────────────────────────────────────────────────

def buy_and_hold(ticker: str, period: str = "2y", init_cash: float = 10_000) -> dict:
    df = get_history(ticker, period=period)
    if df.empty:
        return {"error": "No data"}
    close = df["Close"].squeeze()
    entries = pd.Series(False, index=close.index)
    entries.iloc[0] = True
    exits = pd.Series(False, index=close.index)
    exits.iloc[-1] = True
    pf = vbt.Portfolio.from_signals(close, entries, exits, init_cash=init_cash, freq="1D")
    return _extract_stats(pf, close, ticker, "Buy & Hold")


# ── Strategy: SMA Crossover ───────────────────────────────────────────────────

def sma_crossover(ticker: str, fast: int = 20, slow: int = 50,
                  period: str = "2y", init_cash: float = 10_000) -> dict:
    df = get_history(ticker, period=period)
    if df.empty:
        return {"error": "No data"}
    close = df["Close"].squeeze()
    fast_ma = vbt.MA.run(close, fast).ma
    slow_ma = vbt.MA.run(close, slow).ma
    entries = fast_ma.vbt.crossed_above(slow_ma)
    exits   = fast_ma.vbt.crossed_below(slow_ma)
    pf = vbt.Portfolio.from_signals(close, entries, exits, init_cash=init_cash, freq="1D")
    return _extract_stats(pf, close, ticker, f"SMA {fast}/{slow}")


# ── Strategy: RSI Mean Reversion ─────────────────────────────────────────────

def rsi_strategy(ticker: str, rsi_period: int = 14, oversold: int = 30,
                 overbought: int = 70, period: str = "2y",
                 init_cash: float = 10_000) -> dict:
    df = get_history(ticker, period=period)
    if df.empty:
        return {"error": "No data"}
    close = df["Close"].squeeze()
    rsi   = vbt.RSI.run(close, rsi_period).rsi
    entries = rsi.vbt.crossed_below(oversold)
    exits   = rsi.vbt.crossed_above(overbought)
    pf = vbt.Portfolio.from_signals(close, entries, exits, init_cash=init_cash, freq="1D")
    return _extract_stats(pf, close, ticker, f"RSI({rsi_period}) {oversold}/{overbought}")


# ── Strategy: Bollinger Band Breakout ─────────────────────────────────────────

def bollinger_strategy(ticker: str, bb_period: int = 20, bb_std: float = 2.0,
                       period: str = "2y", init_cash: float = 10_000) -> dict:
    df = get_history(ticker, period=period)
    if df.empty:
        return {"error": "No data"}
    close = df["Close"].squeeze()
    bb    = vbt.BBANDS.run(close, bb_period, bb_std)
    entries = close.vbt.crossed_above(bb.lower)
    exits   = close.vbt.crossed_above(bb.upper)
    pf = vbt.Portfolio.from_signals(close, entries, exits, init_cash=init_cash, freq="1D")
    return _extract_stats(pf, close, ticker, f"BB({bb_period},{bb_std})")


# ── SMA Parameter Sweep (heatmap) ────────────────────────────────────────────

def sma_sweep(ticker: str, fast_range: range = range(10, 51, 5),
              slow_range: range = range(30, 101, 10),
              period: str = "2y", init_cash: float = 10_000) -> pd.DataFrame:
    """Return a pivot table of Sharpe ratios for SMA fast/slow combinations."""
    df = get_history(ticker, period=period)
    if df.empty:
        return pd.DataFrame()
    close = df["Close"].squeeze()
    results = []
    for fast in fast_range:
        for slow in slow_range:
            if fast >= slow:
                continue
            try:
                fm = vbt.MA.run(close, fast).ma
                sm = vbt.MA.run(close, slow).ma
                entries = fm.vbt.crossed_above(sm)
                exits   = fm.vbt.crossed_below(sm)
                pf = vbt.Portfolio.from_signals(close, entries, exits,
                                                init_cash=init_cash, freq="1D")
                sharpe = pf.stats()["Sharpe Ratio"]
                results.append({"fast": fast, "slow": slow, "sharpe": round(sharpe, 3)})
            except Exception:
                continue
    if not results:
        return pd.DataFrame()
    df_res = pd.DataFrame(results)
    return df_res.pivot(index="fast", columns="slow", values="sharpe")


# ── Internal helper ───────────────────────────────────────────────────────────

def _extract_stats(pf, close: pd.Series, ticker: str, strategy: str) -> dict:
    """Pull key stats and equity curve from a vbt Portfolio object."""
    try:
        stats = pf.stats()
        equity = pf.value()
        bh_equity = (close / close.iloc[0]) * pf.init_cash
        trades = pf.trades.records_readable if len(pf.trades.records_readable) > 0 else pd.DataFrame()

        return {
            "ticker":           ticker,
            "strategy":         strategy,
            "equity":           equity,
            "bh_equity":        bh_equity,
            "close":            close,
            "trades":           trades,
            "total_return":     round(float(stats.get("Total Return [%]", 0)), 2),
            "ann_return":       round(float(stats.get("Annualized Return [%]", 0)), 2),
            "sharpe":           round(float(stats.get("Sharpe Ratio", 0)), 3),
            "sortino":          round(float(stats.get("Sortino Ratio", 0)), 3),
            "calmar":           round(float(stats.get("Calmar Ratio", 0)), 3),
            "max_drawdown":     round(float(stats.get("Max Drawdown [%]", 0)), 2),
            "win_rate":         round(float(stats.get("Win Rate [%]", 0)), 2),
            "total_trades":     int(stats.get("Total Trades", 0)),
            "avg_trade_dur":    str(stats.get("Avg Winning Trade Duration", "—")),
            "profit_factor":    round(float(stats.get("Profit Factor", 0)), 3),
            "expectancy":       round(float(stats.get("Expectancy", 0)), 2),
            "init_cash":        pf.init_cash,
            "final_value":      round(float(equity.iloc[-1]), 2),
        }
    except Exception as e:
        return {"error": str(e)}
