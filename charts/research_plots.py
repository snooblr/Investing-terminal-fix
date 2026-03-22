"""
charts/research_plots.py
Plotly charts for the SEC Research page — Investing Visuals theme.
All functions exported: fmt_b, revenue_bar, net_income_bar, margin_trend,
eps_chart, rd_bar, revenue_vs_income, cash_bar, fcf_bar, growth_bar, peer_bar
"""

import plotly.graph_objects as go
import pandas as pd
from config import IV_THEME as T


def fmt_b(val):
    """Format a dollar value in billions."""
    if val is None:
        return "—"
    b = val / 1e9
    if abs(b) >= 1000:
        return f"${b/1000:.1f}T"
    return f"${b:.1f}B"


def _base(title=""):
    return dict(
        paper_bgcolor=T["bg"],
        plot_bgcolor=T["bg2"],
        font=dict(family=T["font_body"], color=T["ink_mid"], size=11),
        title=dict(text=title, font=dict(family=T["font_display"], color=T["ink"], size=14)),
        margin=dict(l=50, r=20, t=45, b=40),
        showlegend=False,
        xaxis=dict(gridcolor="rgba(30,20,10,0.07)", linecolor="rgba(30,20,10,0.15)",
                   tickfont=dict(size=10, color=T["ink_muted"])),
        yaxis=dict(gridcolor="rgba(30,20,10,0.07)", linecolor="rgba(30,20,10,0.15)",
                   tickfont=dict(size=10, color=T["ink_muted"])),
    )


def _safe_df(df):
    return df is not None and not df.empty


def revenue_bar(df, ticker, period="Annual"):
    if not _safe_df(df):
        return go.Figure()
    try:
        labels = list(df["end"].dt.strftime("%Y" if period == "Annual" else "%b %y"))
        vals   = list(df["val"].astype(float) / 1e9)
        colors = [T["s1"] if i == len(vals)-1 else T["s3"] for i in range(len(vals))]
        fig = go.Figure(go.Bar(
            x=labels, y=vals, marker_color=colors,
            text=[f"${v:.1f}B" for v in vals],
            textposition="outside", textfont=dict(size=9, color=T["ink_mid"]),
        ))
        fig.update_layout(**_base(f"{ticker} — {period} Revenue ($B)"),
                          yaxis_tickprefix="$", yaxis_ticksuffix="B")
        return fig
    except Exception:
        return go.Figure()


def net_income_bar(df, ticker):
    if not _safe_df(df):
        return go.Figure()
    try:
        vals   = list(df["val"].astype(float) / 1e9)
        labels = list(df["end"].dt.strftime("%Y"))
        colors = [T["green"] if v >= 0 else T["red"] for v in vals]
        fig = go.Figure(go.Bar(
            x=labels, y=vals, marker_color=colors,
            text=[f"${v:.1f}B" for v in vals],
            textposition="outside", textfont=dict(size=9),
        ))
        fig.update_layout(**_base(f"{ticker} — Net Income ($B)"),
                          yaxis_tickprefix="$", yaxis_ticksuffix="B")
        return fig
    except Exception:
        return go.Figure()


def margin_trend(rev_df, gp_df, ticker):
    if not _safe_df(rev_df) or not _safe_df(gp_df):
        return go.Figure()
    try:
        merged = rev_df.merge(gp_df, on="end", suffixes=("_rev","_gp"))
        merged["margin"] = merged["val_gp"] / merged["val_rev"] * 100
        labels = list(merged["end"].dt.strftime("%Y"))
        vals   = list(merged["margin"].round(1))
        fig = go.Figure(go.Scatter(
            x=labels, y=vals, mode="lines+markers+text",
            line=dict(color=T["ink"], width=2),
            marker=dict(size=6, color=T["ink"]),
            text=[f"{v:.1f}%" for v in vals],
            textposition="top center", textfont=dict(size=9),
        ))
        fig.update_layout(**_base(f"{ticker} — Gross Margin (%)"),
                          yaxis_ticksuffix="%", yaxis_range=[0, 100])
        return fig
    except Exception:
        return go.Figure()


def eps_chart(df, ticker):
    if not _safe_df(df):
        return go.Figure()
    try:
        vals   = list(df["val"].astype(float))
        labels = list(df["end"].dt.strftime("%b %y"))
        colors = [T["green"] if v >= 0 else T["red"] for v in vals]
        fig = go.Figure(go.Bar(
            x=labels, y=vals, marker_color=colors,
            text=[f"${v:.2f}" for v in vals],
            textposition="outside", textfont=dict(size=9),
        ))
        fig.update_layout(**_base(f"{ticker} — Quarterly EPS ($)"),
                          yaxis_tickprefix="$")
        return fig
    except Exception:
        return go.Figure()


def rd_bar(df, ticker):
    if not _safe_df(df):
        return go.Figure()
    try:
        vals   = list(df["val"].astype(float) / 1e9)
        labels = list(df["end"].dt.strftime("%Y"))
        fig = go.Figure(go.Bar(
            x=labels, y=vals, marker_color=T["s2"],
            text=[f"${v:.1f}B" for v in vals],
            textposition="outside", textfont=dict(size=9),
        ))
        fig.update_layout(**_base(f"{ticker} — R&D Spend ($B)"),
                          yaxis_tickprefix="$", yaxis_ticksuffix="B")
        return fig
    except Exception:
        return go.Figure()


def revenue_vs_income(rev_df, net_df, ticker):
    if not _safe_df(rev_df) or not _safe_df(net_df):
        return go.Figure()
    try:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=list(rev_df["end"].dt.strftime("%Y")),
            y=list(rev_df["val"].astype(float) / 1e9),
            name="Revenue", line=dict(color=T["s1"], width=2), mode="lines+markers",
        ))
        fig.add_trace(go.Scatter(
            x=list(net_df["end"].dt.strftime("%Y")),
            y=list(net_df["val"].astype(float) / 1e9),
            name="Net Income", line=dict(color=T["s3"], width=1.5, dash="dash"), mode="lines+markers",
        ))
        layout = _base(f"{ticker} — Revenue vs Net Income ($B)")
        layout["showlegend"] = True
        layout["legend"] = dict(bgcolor="rgba(0,0,0,0)", font=dict(size=10, color=T["ink_mid"]))
        fig.update_layout(**layout, yaxis_tickprefix="$", yaxis_ticksuffix="B")
        return fig
    except Exception:
        return go.Figure()


def cash_bar(df, ticker):
    if not _safe_df(df):
        return go.Figure()
    try:
        vals   = list(df["val"].astype(float) / 1e9)
        labels = list(df["end"].dt.strftime("%Y"))
        colors = [T["s1"] if i == len(vals)-1 else T["s3"] for i in range(len(vals))]
        fig = go.Figure(go.Bar(
            x=labels, y=vals, marker_color=colors,
            text=[f"${v:.1f}B" for v in vals],
            textposition="outside", textfont=dict(size=9, color=T["ink_mid"]),
        ))
        fig.update_layout(**_base(f"{ticker} — Cash & Equivalents ($B)"),
                          yaxis_tickprefix="$", yaxis_ticksuffix="B")
        return fig
    except Exception:
        return go.Figure()


def fcf_bar(df, ticker):
    """Free Cash Flow = Operating Cash Flow - CapEx."""
    if not _safe_df(df):
        return go.Figure()
    try:
        vals   = list(df["val"].astype(float) / 1e9)
        labels = list(df["end"].dt.strftime("%Y"))
        colors = [T["green"] if v >= 0 else T["red"] for v in vals]
        fig = go.Figure(go.Bar(
            x=labels, y=vals, marker_color=colors,
            text=[f"${v:.1f}B" for v in vals],
            textposition="outside", textfont=dict(size=9),
        ))
        fig.update_layout(**_base(f"{ticker} — Free Cash Flow ($B)"),
                          yaxis_tickprefix="$", yaxis_ticksuffix="B")
        return fig
    except Exception:
        return go.Figure()


def growth_bar(df, ticker, period="Annual"):
    """Revenue YoY growth % chart."""
    if not _safe_df(df):
        return go.Figure()
    try:
        vals   = list(df["val"].astype(float).round(1))
        labels = list(df["end"].dt.strftime("%Y" if period == "Annual" else "%b %y"))
        colors = [T["green"] if v >= 0 else T["red"] for v in vals]
        fig = go.Figure(go.Bar(
            x=labels, y=vals, marker_color=colors,
            text=[f"{v:+.1f}%" for v in vals],
            textposition="outside", textfont=dict(size=9),
        ))
        fig.update_layout(**_base(f"{ticker} — Revenue Growth YoY (%)"),
                          yaxis_ticksuffix="%")
        return fig
    except Exception:
        return go.Figure()


def peer_bar(peer_data: dict, metric: str, label: str):
    """
    Compare a metric across multiple tickers.
    peer_data: { "NVDA": 130.5, "AMD": 25.8, "INTC": 54.2 }
    """
    if not peer_data:
        return go.Figure()
    try:
        tickers = list(peer_data.keys())
        vals    = list(peer_data.values())
        colors  = [T["s1"] if i == 0 else T["s3"] for i in range(len(tickers))]
        is_pct  = "%" in label
        text    = [f"{v:.1f}%" if is_pct else f"${v:.1f}B" for v in vals]
        fig = go.Figure(go.Bar(
            x=tickers, y=vals, marker_color=colors,
            text=text, textposition="outside", textfont=dict(size=11, color=T["ink_mid"]),
        ))
        suffix = "%" if is_pct else "B"
        prefix = "" if is_pct else "$"
        fig.update_layout(**_base(f"Peer Comparison — {label}"),
                          yaxis_tickprefix=prefix, yaxis_ticksuffix=suffix)
        return fig
    except Exception:
        return go.Figure()


def margin_stack(fin: dict, ticker: str):
    """Gross, Operating, and Net margin on one chart."""
    rev_a = fin.get("rev_annual")
    gp_a  = fin.get("gp_annual")
    op_a  = fin.get("op_annual")
    net_a = fin.get("net_annual")
    if not _safe_df(rev_a):
        return go.Figure()
    try:
        fig = go.Figure()
        pairs = [
            (gp_a,  "Gross Margin",     T["s1"]),
            (op_a,  "Operating Margin", T["s2"]),
            (net_a, "Net Margin",       T["s3"]),
        ]
        for df2, name, color in pairs:
            if not _safe_df(df2):
                continue
            merged = rev_a.merge(df2, on="end", suffixes=("_rev","_x"))
            merged["pct"] = merged["val_x"] / merged["val_rev"] * 100
            fig.add_trace(go.Scatter(
                x=list(merged["end"].dt.strftime("%Y")),
                y=list(merged["pct"].round(1)),
                name=name, line=dict(color=color, width=1.8), mode="lines+markers",
            ))
        layout = _base(f"{ticker} — Margin Stack (%)")
        layout["showlegend"] = True
        layout["legend"] = dict(bgcolor="rgba(0,0,0,0)", font=dict(size=10, color=T["ink_mid"]))
        fig.update_layout(**layout, yaxis_ticksuffix="%")
        return fig
    except Exception:
        return go.Figure()
