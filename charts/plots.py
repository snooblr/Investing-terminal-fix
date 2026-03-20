"""
charts/plots.py
All Plotly figures — every chart uses the Investing Visuals design system.
"""

import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
from config import IV_THEME as T


# ── Theme helpers ─────────────────────────────────────────────────────────────

def _base_layout(**kwargs) -> dict:
    return dict(
        paper_bgcolor=T["bg"],
        plot_bgcolor=T["bg2"],
        font=dict(family=T["font_body"], color=T["ink_mid"], size=12),
        title_font=dict(family=T["font_display"], color=T["ink"], size=16),
        xaxis=dict(gridcolor="rgba(30,20,10,0.08)", linecolor="rgba(30,20,10,0.2)",
                   tickfont=dict(size=11, color=T["ink_muted"])),
        yaxis=dict(gridcolor="rgba(30,20,10,0.08)", linecolor="rgba(30,20,10,0.2)",
                   tickfont=dict(size=11, color=T["ink_muted"])),
        margin=dict(l=50, r=20, t=50, b=40),
        legend=dict(bgcolor="rgba(0,0,0,0)", borderwidth=0,
                    font=dict(size=11, color=T["ink_mid"])),
        **kwargs,
    )


def _ink_series(n: int) -> list:
    """Monochromatic ink ramp for multiple series."""
    ramp = [T["s1"], T["s2"], T["s3"], T["s4"], "#888888", "#bbbbbb"]
    return ramp[:n]


# ── Candlestick + Volume ──────────────────────────────────────────────────────

def candlestick_chart(df: pd.DataFrame, ticker: str) -> go.Figure:
    fig = go.Figure()
    df = df.copy()
    close_col = "Close" if "Close" in df.columns else df.columns[0]

    # Candlestick
    if all(c in df.columns for c in ["Open", "High", "Low", "Close"]):
        fig.add_trace(go.Candlestick(
            x=df.index,
            open=df["Open"], high=df["High"],
            low=df["Low"],  close=df["Close"],
            increasing=dict(line=dict(color=T["green"], width=1),
                            fillcolor=T["green_bg"]),
            decreasing=dict(line=dict(color=T["red"], width=1),
                            fillcolor=T["red_bg"]),
            name=ticker, showlegend=False,
        ))
    else:
        fig.add_trace(go.Scatter(
            x=df.index, y=df[close_col],
            line=dict(color=T["ink"], width=1.5),
            name=ticker, showlegend=False,
        ))

    # Volume subplot
    if "Volume" in df.columns:
        colors = [T["green"] if df["Close"].iloc[i] >= df["Open"].iloc[i]
                  else T["red"] for i in range(len(df))] if "Open" in df.columns \
                 else [T["s3"]] * len(df)
        fig.add_trace(go.Bar(
            x=df.index, y=df["Volume"],
            marker_color=colors, opacity=0.4,
            name="Volume", yaxis="y2", showlegend=False,
        ))
        fig.update_layout(
            yaxis2=dict(overlaying="y", side="right", showgrid=False,
                        tickfont=dict(size=9, color=T["ink_muted"]),
                        domain=[0, 0.2]),
            yaxis=dict(domain=[0.25, 1]),
        )

    fig.update_layout(
        **_base_layout(title=f"{ticker} — Price & Volume"),
        xaxis_rangeslider_visible=False,
        hovermode="x unified",
    )
    return fig


def line_chart(df: pd.DataFrame, ticker: str, col: str = "Close") -> go.Figure:
    """Simple line chart with fill."""
    fig = go.Figure()
    series = df[col] if col in df.columns else df.iloc[:, 0]
    up = series.iloc[-1] >= series.iloc[0]
    color = T["green"] if up else T["red"]
    fill_color = "rgba(45,106,45,0.08)" if up else "rgba(139,32,32,0.08)"
    fig.add_trace(go.Scatter(
        x=df.index, y=series,
        line=dict(color=color, width=1.8),
        fill="tozeroy", fillcolor=fill_color,
        name=ticker,
    ))
    fig.update_layout(**_base_layout(title=f"{ticker}"), showlegend=False)
    return fig


# ── Portfolio ─────────────────────────────────────────────────────────────────

def portfolio_bar(df: pd.DataFrame) -> go.Figure:
    colors = [T["green"] if v >= 0 else T["red"] for v in df["P&L ($)"]]
    fig = go.Figure(go.Bar(
        x=df["Ticker"], y=df["P&L ($)"],
        marker_color=colors,
        text=[f"${v:,.0f}" for v in df["P&L ($)"]],
        textposition="outside",
        textfont=dict(size=11),
    ))
    fig.update_layout(**_base_layout(title="Unrealised P&L by Position"),
                      showlegend=False)
    return fig


def portfolio_donut(df: pd.DataFrame) -> go.Figure:
    colors = _ink_series(len(df))
    fig = go.Figure(go.Pie(
        labels=df["Ticker"],
        values=df["Mkt Value"],
        hole=0.55,
        marker=dict(colors=colors, line=dict(color=T["bg"], width=2)),
        textinfo="label+percent",
        textfont=dict(size=11, family=T["font_body"]),
    ))
    fig.update_layout(**_base_layout(title="Portfolio Allocation"),
                      showlegend=False)
    return fig


def cumulative_returns_chart(returns_dict: dict) -> go.Figure:
    """Plot cumulative return curves for multiple series."""
    fig = go.Figure()
    colors = _ink_series(len(returns_dict))
    for i, (label, series) in enumerate(returns_dict.items()):
        cumret = (1 + series).cumprod() - 1
        fig.add_trace(go.Scatter(
            x=cumret.index, y=cumret * 100,
            name=label,
            line=dict(color=colors[i], width=1.5 if i == 0 else 1.2),
        ))
    fig.update_layout(
        **_base_layout(title="Cumulative Returns (%)"),
        yaxis_ticksuffix="%",
        hovermode="x unified",
    )
    return fig


def drawdown_chart(drawdown: pd.Series, label: str = "Portfolio") -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=drawdown.index, y=drawdown,
        fill="tozeroy", fillcolor="rgba(139,32,32,0.15)",
        line=dict(color=T["red"], width=1.2),
        name=label,
    ))
    fig.update_layout(
        **_base_layout(title="Drawdown (%)"),
        yaxis_ticksuffix="%", showlegend=False,
    )
    return fig


def correlation_heatmap(corr: pd.DataFrame) -> go.Figure:
    fig = go.Figure(go.Heatmap(
        z=corr.values,
        x=corr.columns.tolist(),
        y=corr.index.tolist(),
        colorscale=[[0, T["bg"]], [0.5, T["s3"]], [1, T["s1"]]],
        zmid=0,
        text=corr.round(2).values,
        texttemplate="%{text}",
        textfont=dict(size=11),
        colorbar=dict(tickfont=dict(size=10, color=T["ink_muted"])),
    ))
    fig.update_layout(**_base_layout(title="Correlation Matrix"))
    return fig


# ── Backtest ──────────────────────────────────────────────────────────────────

def equity_curve_chart(result: dict) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=result["equity"].index, y=result["equity"],
        name=result["strategy"],
        line=dict(color=T["ink"], width=1.8),
    ))
    fig.add_trace(go.Scatter(
        x=result["bh_equity"].index, y=result["bh_equity"],
        name="Buy & Hold",
        line=dict(color=T["s3"], width=1.2, dash="dash"),
    ))
    # Trade markers
    trades = result.get("trades", pd.DataFrame())
    if not trades.empty and "Entry Timestamp" in trades.columns:
        fig.add_trace(go.Scatter(
            x=trades["Entry Timestamp"], y=trades.get("Entry Price", []),
            mode="markers",
            marker=dict(symbol="triangle-up", size=8, color=T["green"]),
            name="Entry",
        ))
    fig.update_layout(
        **_base_layout(title=f"{result['ticker']} — Equity Curve: {result['strategy']}"),
        hovermode="x unified",
    )
    return fig


def sma_heatmap(pivot: pd.DataFrame, ticker: str) -> go.Figure:
    fig = go.Figure(go.Heatmap(
        z=pivot.values,
        x=[str(c) for c in pivot.columns],
        y=[str(i) for i in pivot.index],
        colorscale=[[0, T["red_bg"]], [0.5, T["bg2"]], [1, T["green_bg"]]],
        text=pivot.round(2).values,
        texttemplate="%{text}",
        textfont=dict(size=10),
        colorbar=dict(title="Sharpe", tickfont=dict(size=10)),
    ))
    fig.update_layout(
        **_base_layout(title=f"{ticker} — SMA Crossover Sharpe Heatmap"),
        xaxis_title="Slow MA", yaxis_title="Fast MA",
    )
    return fig


# ── Optimiser ─────────────────────────────────────────────────────────────────

def efficient_frontier_chart(frontier: pd.DataFrame,
                              opt_vol: float, opt_ret: float,
                              opt_sharpe: float) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=frontier["volatility"], y=frontier["return"],
        mode="lines",
        line=dict(color=T["ink"], width=2),
        name="Efficient Frontier",
    ))
    fig.add_trace(go.Scatter(
        x=[opt_vol], y=[opt_ret],
        mode="markers+text",
        marker=dict(size=12, color=T["ink"], symbol="star"),
        text=[f"Sharpe {opt_sharpe:.2f}"],
        textposition="top right",
        textfont=dict(size=11),
        name="Optimal Portfolio",
    ))
    fig.update_layout(
        **_base_layout(title="Efficient Frontier"),
        xaxis_title="Annualised Volatility (%)",
        yaxis_title="Annualised Return (%)",
        xaxis_ticksuffix="%", yaxis_ticksuffix="%",
    )
    return fig


def weights_bar(weights: dict) -> go.Figure:
    w = {k: v for k, v in weights.items() if v > 0.001}
    fig = go.Figure(go.Bar(
        x=list(w.keys()),
        y=[v * 100 for v in w.values()],
        marker_color=_ink_series(len(w)),
        text=[f"{v*100:.1f}%" for v in w.values()],
        textposition="outside",
        textfont=dict(size=11),
    ))
    fig.update_layout(
        **_base_layout(title="Optimal Weights"),
        yaxis_ticksuffix="%", showlegend=False,
    )
    return fig
