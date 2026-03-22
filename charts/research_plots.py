"""
charts/research_plots.py
Plotly charts for the SEC Research page — Investing Visuals theme.
"""

import plotly.graph_objects as go
import pandas as pd
from config import IV_THEME as T


def fmt_b(val):
    if val is None:
        return "—"
    b = val / 1e9
    if b >= 1000:
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


def revenue_bar(df, ticker, period="Annual"):
    if df is None or df.empty:
        return go.Figure()
    try:
        labels = list(df["end"].dt.strftime("%Y" if period == "Annual" else "%b %y"))
        vals   = list(df["val"].astype(float) / 1e9)
        colors = [T["s1"] if i == len(vals)-1 else T["s3"] for i in range(len(vals))]
        fig = go.Figure(go.Bar(
            x=labels, y=vals, marker_color=colors,
            text=[f"${v:.1f}B" for v in vals],
            textposition="outside", textfont=dict(size=10, color=T["ink_mid"]),
        ))
        fig.update_layout(**_base(f"{ticker} — {period} Revenue ($B)"),
                          yaxis_tickprefix="$", yaxis_ticksuffix="B")
        return fig
    except Exception:
        return go.Figure()


def net_income_bar(df, ticker):
    if df is None or df.empty:
        return go.Figure()
    try:
        vals   = list(df["val"].astype(float) / 1e9)
        labels = list(df["end"].dt.strftime("%Y"))
        colors = [T["green"] if v >= 0 else T["red"] for v in vals]
        fig = go.Figure(go.Bar(
            x=labels, y=vals, marker_color=colors,
            text=[f"${v:.1f}B" for v in vals],
            textposition="outside", textfont=dict(size=10),
        ))
        fig.update_layout(**_base(f"{ticker} — Annual Net Income ($B)"),
                          yaxis_tickprefix="$", yaxis_ticksuffix="B")
        return fig
    except Exception:
        return go.Figure()


def margin_trend(rev_df, gp_df, ticker):
    if rev_df is None or gp_df is None or rev_df.empty or gp_df.empty:
        return go.Figure()
    try:
        merged = rev_df.merge(gp_df, on="end", suffixes=("_rev", "_gp"))
        merged["margin"] = merged["val_gp"] / merged["val_rev"] * 100
        labels = list(merged["end"].dt.strftime("%Y"))
        vals   = list(merged["margin"].round(1))
        fig = go.Figure(go.Scatter(
            x=labels, y=vals,
            mode="lines+markers+text",
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
    if df is None or df.empty:
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
    if df is None or df.empty:
        return go.Figure()
    try:
        vals   = list(df["val"].astype(float) / 1e9)
        labels = list(df["end"].dt.strftime("%Y"))
        fig = go.Figure(go.Bar(
            x=labels, y=vals, marker_color=T["s2"],
            text=[f"${v:.1f}B" for v in vals],
            textposition="outside", textfont=dict(size=10),
        ))
        fig.update_layout(**_base(f"{ticker} — R&D Spend ($B)"),
                          yaxis_tickprefix="$", yaxis_ticksuffix="B")
        return fig
    except Exception:
        return go.Figure()


def revenue_vs_income(rev_df, net_df, ticker):
    if rev_df is None or net_df is None or rev_df.empty or net_df.empty:
        return go.Figure()
    try:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=list(rev_df["end"].dt.strftime("%Y")),
            y=list(rev_df["val"].astype(float) / 1e9),
            name="Revenue",
            line=dict(color=T["s1"], width=2),
            mode="lines+markers",
        ))
        fig.add_trace(go.Scatter(
            x=list(net_df["end"].dt.strftime("%Y")),
            y=list(net_df["val"].astype(float) / 1e9),
            name="Net Income",
            line=dict(color=T["s3"], width=1.5, dash="dash"),
            mode="lines+markers",
        ))
        layout = _base(f"{ticker} — Revenue vs Net Income ($B)")
        layout["showlegend"] = True
        layout["legend"] = dict(bgcolor="rgba(0,0,0,0)", font=dict(size=10, color=T["ink_mid"]))
        fig.update_layout(**layout, yaxis_tickprefix="$", yaxis_ticksuffix="B")
        return fig
    except Exception:
        return go.Figure()
