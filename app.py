"""
app.py — Personal Bloomberg Terminal
Investing Visuals · yfinance · pandas · plotly · vectorbt · PyPortfolioOpt
"""

import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime
import plotly.graph_objects as go
import requests

st.set_page_config(
    page_title="Terminal · Investing Visuals",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;700;800&family=DM+Sans:wght@300;400;500&display=swap" rel="stylesheet">
<style>
  html, body, [class*="css"] { font-family: 'DM Sans', sans-serif !important; color: #111111; }
  .stApp { background-color: #f2ede4; }
  section[data-testid="stSidebar"] { background-color: #111111; }
  section[data-testid="stSidebar"] * { color: #e8e2d6 !important; }
  h1,h2,h3 { font-family:'Playfair Display',Georgia,serif !important; color:#111111 !important; }
  h1 { font-size:28px; font-weight:800; }
  h2 { font-size:20px; font-weight:700; }
  h3 { font-size:16px; font-weight:700; }
  p, li, span, div, label { color: #111111; }
  [data-testid="metric-container"] {
    background:#ffffff; border:1px solid rgba(30,20,10,0.13);
    border-radius:6px; padding:12px 16px;
  }
  [data-testid="metric-container"] label {
    font-size:10px !important; font-weight:500 !important;
    letter-spacing:0.08em !important; text-transform:uppercase !important;
    color:#888888 !important;
  }
  [data-testid="metric-container"] [data-testid="stMetricValue"] {
    font-family:'Playfair Display',serif !important;
    font-size:22px !important; font-weight:700 !important; color:#111111 !important;
  }
  [data-testid="stMetricDelta"] { font-size:12px !important; }
  .stDataFrame { border:1px solid rgba(30,20,10,0.13); border-radius:6px; }
  .stButton>button {
    background:#111111; color:#f2ede4; border:none; border-radius:4px;
    font-family:'DM Sans',sans-serif; font-size:12px; font-weight:500;
    letter-spacing:0.06em; padding:6px 16px;
  }
  .stButton>button:hover { background:#333333; }
  hr { border-color:rgba(30,20,10,0.13); }
  .tag { display:inline-block; font-size:9px; font-weight:500; letter-spacing:0.1em;
    text-transform:uppercase; border:1px solid rgba(30,20,10,0.2); padding:2px 7px;
    border-radius:3px; color:#888888; margin-right:4px; }
  .tag-up   { color:#2d6a2d; border-color:#2d6a2d; background:#e8f0e8; }
  .tag-down { color:#8b2020; border-color:#8b2020; background:#f0e8e8; }
  .exp-wrap { background:#e8e2d6; border-radius:4px; height:10px; width:100%; }
  .exp-bar  { height:10px; border-radius:4px; background:#1a1a1a; }
  .stSelectbox div[data-baseweb="select"] span { color:#111111 !important; }
  .stSelectbox div[data-baseweb="select"] { background-color:#ffffff !important; }
  .stSelectbox label { color:#111111 !important; }
</style>
""", unsafe_allow_html=True)

from config import (WATCHLIST, PORTFOLIO, BACKTEST_TICKERS, OPTIMISER_TICKERS,
                    RETURNS_EXCLUDE, DAD_PORTFOLIO, DAD_RETURNS_EXCLUDE, IV_THEME as T)
from data.fetcher import get_history, get_multi_history, get_quote, get_watchlist_quotes, get_intraday
from analysis.portfolio import (build_portfolio_df, portfolio_summary,
                                 get_portfolio_returns, compute_metrics, drawdown_series)
from analysis.optimizer import run_optimisation, efficient_frontier_curve, discrete_allocation, correlation_matrix
from analysis.backtest import buy_and_hold, sma_crossover, rsi_strategy, bollinger_strategy, sma_sweep
from charts.plots import (candlestick_chart, line_chart, portfolio_bar, portfolio_donut,
                           cumulative_returns_chart, drawdown_chart, correlation_heatmap,
                           equity_curve_chart, sma_heatmap, efficient_frontier_chart, weights_bar)

AV_KEY = "GAMWJOKIFEQ94I69"


def safe(val, fmt=".2f", prefix="", suffix=""):
    try:
        if val is None or (isinstance(val, float) and np.isnan(val)):
            return "—"
        return f"{prefix}{val:{fmt}}{suffix}"
    except Exception:
        return "—"


def safe_pct(pct):
    """Convert pct to int safely, handling NaN."""
    try:
        v = float(pct)
        if np.isnan(v):
            return 0
        return min(int(v), 100)
    except Exception:
        return 0


@st.cache_data(ttl=3600, show_spinner=False)
def get_dividend_data(ticker):
    """Fetch real trailing 12M dividend data from Alpha Vantage."""
    try:
        r = requests.get("https://www.alphavantage.co/query",
            params={"function": "DIVIDENDS", "symbol": ticker, "apikey": AV_KEY},
            timeout=8)
        data = r.json()
        if "data" not in data or not data["data"]:
            return {"annual_div": 0, "yield_pct": 0, "payments": 0}
        df = pd.DataFrame(data["data"])
        df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
        df["ex_dividend_date"] = pd.to_datetime(df["ex_dividend_date"], errors="coerce")
        df = df.dropna(subset=["amount", "ex_dividend_date"])
        cutoff = pd.Timestamp.now() - pd.DateOffset(months=12)
        df = df[df["ex_dividend_date"] >= cutoff]
        if df.empty:
            return {"annual_div": 0, "yield_pct": 0, "payments": 0}
        annual = float(df["amount"].sum())
        return {"annual_div": round(annual, 4), "payments": len(df)}
    except Exception:
        return {"annual_div": 0, "yield_pct": 0, "payments": 0}


def render_portfolio_page(port_dict, exclude_list, label="Portfolio", rf=0.04):
    with st.spinner(f"Fetching {label} prices..."):
        df      = build_portfolio_df(port_dict)
        summary = portfolio_summary(df)

    if df.empty:
        st.warning("No data available.")
        return

    # Summary cards
    m1,m2,m3,m4,m5 = st.columns(5)
    m1.metric("Total Value",  f"${summary['total_value']:,.0f}")
    m2.metric("Total P&L",    f"${summary['total_pnl']:,.0f}",  delta=f"{summary['total_pnl_pct']:+.2f}%")
    m3.metric("Day P&L",      f"${summary['day_pnl']:,.0f}",   delta=f"{summary['day_pnl_pct']:+.2f}%")
    m4.metric("Cost Basis",   f"${summary['total_cost']:,.0f}")
    m5.metric("Positions",    summary['num_positions'])

    st.markdown("---")

    # Charts
    c1,c2 = st.columns(2)
    with c1: st.plotly_chart(portfolio_bar(df),   use_container_width=True)
    with c2: st.plotly_chart(portfolio_donut(df), use_container_width=True)

    # Positions table
    st.markdown("### Positions")
    disp = df[["Ticker","Name","Qty","Avg Cost","Last Price","Mkt Value","P&L ($)","P&L (%)","Day P&L ($)","Sector"]].copy()
    disp["Avg Cost"]    = disp["Avg Cost"].apply(lambda x: f"${x:,.2f}")
    disp["Last Price"]  = disp["Last Price"].apply(lambda x: f"${x:,.2f}")
    disp["Mkt Value"]   = disp["Mkt Value"].apply(lambda x: f"${x:,.0f}")
    disp["P&L ($)"]     = disp["P&L ($)"].apply(lambda x: f"${x:,.0f}")
    disp["P&L (%)"]     = disp["P&L (%)"].apply(lambda x: f"{x:+.2f}%")
    disp["Day P&L ($)"] = disp["Day P&L ($)"].apply(lambda x: f"${x:+,.0f}")
    st.dataframe(disp, use_container_width=True, hide_index=True)

    # Risk metrics
    st.markdown("---")
    st.markdown("### Risk Metrics")
    tickers_list  = [t for t in port_dict.keys() if t not in exclude_list]
    quotes_map    = {t: get_quote(t) for t in tickers_list}
    valid_tickers = [t for t in tickers_list if quotes_map.get(t) and quotes_map[t].get("price")]
    total_val     = sum(port_dict[t]["qty"] * quotes_map[t]["price"] for t in valid_tickers)

    if total_val == 0:
        st.warning("Could not compute risk metrics.")
        return

    weights = {t: (port_dict[t]["qty"] * quotes_map[t]["price"]) / total_val for t in valid_tickers}

    with st.spinner("Computing returns..."):
        port_ret = get_portfolio_returns(valid_tickers, weights, period="2y")
        spy_hist = get_history("SPY", period="2y")
        spy_ret  = spy_hist["Close"].squeeze().pct_change().dropna() if not spy_hist.empty else pd.Series(dtype=float)
        metrics  = compute_metrics(port_ret, rf=rf)
        dd       = drawdown_series(port_ret) if not port_ret.empty else pd.Series(dtype=float)

    if metrics:
        r1,r2,r3,r4,r5 = st.columns(5)
        r1.metric("Ann. Return",  safe(metrics.get("ann_return"),  fmt="+.2f", suffix="%"))
        r2.metric("Ann. Vol",     safe(metrics.get("ann_vol"),     suffix="%"))
        r3.metric("Sharpe",       safe(metrics.get("sharpe"),      fmt=".3f"))
        r4.metric("Sortino",      safe(metrics.get("sortino"),     fmt=".3f"))
        r5.metric("Max Drawdown", safe(metrics.get("max_drawdown"),suffix="%"))
        r1b,r2b,r3b,r4b,r5b = st.columns(5)
        r1b.metric("Total Return", safe(metrics.get("total_return"),fmt="+.2f", suffix="%"))
        r2b.metric("Calmar",       safe(metrics.get("calmar"),      fmt=".3f"))
        r3b.metric("VaR 95%",      safe(metrics.get("var_95"),      suffix="%"))
        r4b.metric("CVaR 95%",     safe(metrics.get("cvar_95"),     suffix="%"))
        r5b.metric("Win Rate",     safe(metrics.get("win_rate"),    suffix="%"))
    else:
        st.info("Not enough history to compute risk metrics.")

    if not port_ret.empty and not spy_ret.empty:
        p_al, s_al = port_ret.align(spy_ret, join="inner")
        if not p_al.empty:
            st.plotly_chart(
                cumulative_returns_chart({label: p_al, "SPY Benchmark": s_al}),
                use_container_width=True)
            if not dd.empty:
                st.plotly_chart(drawdown_chart(dd, label), use_container_width=True)

    # Correlation
    st.markdown("---")
    st.markdown("### Correlation Matrix")
    st.caption("Low numbers = better diversification. Above 0.7 = moves together.")
    with st.spinner("Computing correlation..."):
        corr = correlation_matrix(valid_tickers, period="2y")
    if not corr.empty:
        st.plotly_chart(correlation_heatmap(corr), use_container_width=True)

    # Sector & Beta
    st.markdown("---")
    st.markdown("### Sector & Beta Exposure")
    sector_data, beta_data = {}, {}
    port_total = df["Mkt Value"].sum()

    for _, row in df.iterrows():
        sec = str(row.get("Sector") or "Unknown")
        v   = float(row["Mkt Value"]) if not pd.isna(row["Mkt Value"]) else 0
        sector_data[sec] = sector_data.get(sec, 0) + v
        b = row.get("Beta")
        if b is not None and not pd.isna(b):
            beta_data[row["Ticker"]] = float(b)

    sc1, sc2 = st.columns(2)
    with sc1:
        st.markdown("**Sector Concentration**")
        for sec, val in sorted(sector_data.items(), key=lambda x: x[1], reverse=True):
            pct = (val / port_total * 100) if port_total else 0
            w   = safe_pct(pct)
            st.markdown(
                f"<div style='margin-bottom:8px;'>"
                f"<div style='display:flex;justify-content:space-between;font-size:12px;margin-bottom:3px;color:#111;'>"
                f"<span>{sec}</span><span style='font-weight:500;'>{pct:.1f}%</span></div>"
                f"<div class='exp-wrap'><div class='exp-bar' style='width:{w}%;'></div></div>"
                f"</div>", unsafe_allow_html=True)

    with sc2:
        st.markdown("**Beta by Position**")
        st.caption("Beta > 1 = more volatile than market.")
        if beta_data:
            port_beta = sum(
                beta_data.get(t, 1.0) * (port_dict[t]["qty"] * quotes_map.get(t, {}).get("price", 0)) / total_val
                for t in valid_tickers if t in beta_data
            )
            beta_df = pd.DataFrame([
                {"Ticker": t, "Beta": round(b, 2),
                 "vs Market": "High vol" if b > 1.5 else "Above" if b > 1.0 else "Below"}
                for t, b in sorted(beta_data.items(), key=lambda x: x[1], reverse=True)
            ])
            st.dataframe(beta_df, use_container_width=True, hide_index=True)
            st.metric("Weighted Portfolio Beta", f"{port_beta:.2f}")


def render_dividend_tracker(port_dict):
    st.markdown("---")
    st.markdown("### Dividend & Income Tracker")
    st.caption("Real trailing 12-month distributions via Alpha Vantage.")

    rows = []
    for tkr, pos in port_dict.items():
        try:
            q = get_quote(tkr)
            if not q or not q.get("price"):
                continue
            price    = float(q["price"])
            qty      = pos["qty"]
            avg_cost = pos["avg_cost"]
            mkt_val  = qty * price

            div_data = get_dividend_data(tkr)
            div_rate = div_data.get("annual_div", 0)
            n_pays   = div_data.get("payments", 0)
            cur_yld  = round(div_rate / price * 100, 2) if price and div_rate else 0
            ann_inc  = div_rate * qty
            mon_inc  = ann_inc / 12
            yoc      = round(div_rate / avg_cost * 100, 2) if avg_cost > 0 and div_rate > 0 else 0

            rows.append({
                "Ticker":         tkr,
                "Mkt Value":      round(mkt_val, 2),
                "Ann. Div/Share": round(div_rate, 4),
                "Current Yield":  cur_yld,
                "Yield on Cost":  yoc,
                "Monthly Income": round(mon_inc, 2),
                "Annual Income":  round(ann_inc, 2),
                "Payments/Yr":    n_pays if n_pays else "—",
                "_pays":          div_rate > 0,
            })
        except Exception:
            continue

    if not rows:
        st.info("No dividend data found.")
        return

    div_df        = pd.DataFrame(rows)
    total_monthly = div_df["Monthly Income"].sum()
    total_annual  = div_df["Annual Income"].sum()
    total_mv      = div_df["Mkt Value"].sum()
    port_yld      = round(total_annual / total_mv * 100, 2) if total_mv else 0
    paying        = int(div_df["_pays"].sum())

    d1,d2,d3,d4 = st.columns(4)
    d1.metric("Monthly Income",   f"${total_monthly:,.2f}")
    d2.metric("Annual Income",    f"${total_annual:,.2f}")
    d3.metric("Portfolio Yield",  f"{port_yld:.2f}%")
    d4.metric("Paying Positions", f"{paying}/{len(div_df)}")

    paying_df = div_df[div_df["_pays"]].sort_values("Annual Income", ascending=False).copy()
    if not paying_df.empty:
        st.markdown("#### Income by Position")
        disp = paying_df.copy()
        disp["Mkt Value"]      = disp["Mkt Value"].apply(lambda x: f"${x:,.0f}")
        disp["Ann. Div/Share"] = disp["Ann. Div/Share"].apply(lambda x: f"${x:.4f}")
        disp["Current Yield"]  = disp["Current Yield"].apply(lambda x: f"{x:.2f}%")
        disp["Yield on Cost"]  = disp["Yield on Cost"].apply(lambda x: f"{x:.2f}%")
        disp["Monthly Income"] = disp["Monthly Income"].apply(lambda x: f"${x:,.2f}")
        disp["Annual Income"]  = disp["Annual Income"].apply(lambda x: f"${x:,.2f}")
        st.dataframe(disp.drop(columns=["_pays"]), use_container_width=True, hide_index=True)

        bar_data = paying_df.sort_values("Annual Income", ascending=True)
        fig = go.Figure(go.Bar(
            x=bar_data["Annual Income"], y=bar_data["Ticker"],
            orientation="h", marker_color=T["ink"],
            text=[f"${v:,.2f}" for v in bar_data["Annual Income"]],
            textposition="outside", textfont=dict(size=10),
        ))
        fig.update_layout(
            paper_bgcolor=T["bg"], plot_bgcolor=T["bg2"],
            font=dict(family=T["font_body"], color=T["ink_mid"], size=11),
            title=dict(text="Annual Income by Position",
                       font=dict(family=T["font_display"], size=15, color=T["ink"])),
            xaxis=dict(tickprefix="$", gridcolor="rgba(30,20,10,0.08)"),
            yaxis=dict(gridcolor="rgba(30,20,10,0.08)"),
            margin=dict(l=60,r=80,t=50,b=30),
            showlegend=False,
            height=max(300, len(bar_data) * 28),
        )
        st.plotly_chart(fig, use_container_width=True)

    non_paying = div_df[~div_df["_pays"]]["Ticker"].tolist()
    if non_paying:
        st.caption(f"No dividend data: {', '.join(non_paying)}")


# ═══════════════════════════════════════════════════════════════════════════════
#  SIDEBAR
# ═══════════════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown("## 📈 Terminal")
    page = st.radio("", ["Chart", "My Portfolio", "Dad's Portfolio",
                         "Watchlist", "Backtest", "Optimiser", "Research"],
                    label_visibility="collapsed")
    st.markdown("---")
    rf_rate = st.slider("Risk-free rate (%)", 0.0, 8.0, 4.0, 0.25) / 100
    if st.button("🔄 Clear cache"):
        st.cache_data.clear()
        st.success("Cache cleared.")
    st.markdown("---")
    st.markdown('<span style="font-size:9px;color:#aaa;letter-spacing:0.08em;">NOT FINANCIAL ADVICE · @INVESTINGVISUALS</span>',
                unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
#  PAGE: CHART
# ═══════════════════════════════════════════════════════════════════════════════

if page == "Chart":
    c1,c2 = st.columns([3,1])
    with c1: st.markdown("# Chart")
    with c2: ticker = st.text_input("", value="NVDA", label_visibility="collapsed").upper()

    tf_map = {"1D":("1d","5m"),"1W":("5d","30m"),"1M":("1mo","1d"),
              "3M":("3mo","1d"),"YTD":("ytd","1d"),"1Y":("1y","1d"),"2Y":("2y","1wk")}
    tf = st.radio("", list(tf_map.keys()), horizontal=True, index=5, label_visibility="collapsed")
    period, interval = tf_map[tf]

    with st.spinner(f"Fetching {ticker}..."):
        df    = get_intraday(ticker) if tf == "1D" else get_history(ticker, period=period, interval=interval)
        quote = get_quote(ticker)

    if df.empty or not quote or not quote.get("price"):
        st.error(f"Could not load data for {ticker}.")
    else:
        up      = quote["chg"] >= 0
        chg_tag = "tag-up" if up else "tag-down"
        st.markdown(
            f"**{quote['name']}** &nbsp;"
            f"<span style='font-family:Playfair Display,serif;font-size:28px;font-weight:800;color:#111;'>${quote['price']:,.2f}</span> &nbsp;"
            f"<span class='tag {chg_tag}'>{quote['chg']:+.2f} ({quote['chg_pct']:+.2f}%)</span>"
            f"<span class='tag'>Vol {quote['volume']:,.0f}</span>",
            unsafe_allow_html=True)
        st.plotly_chart(candlestick_chart(df, ticker), use_container_width=True)
        st.markdown("### Key Statistics")
        s1,s2,s3,s4 = st.columns(4)
        s1.metric("Market Cap",  f"${quote['mkt_cap']/1e9:.1f}B" if quote.get('mkt_cap') else "—")
        s2.metric("P/E (TTM)",   safe(quote.get("pe")))
        s3.metric("52W High",    f"${quote['week52_high']:,.2f}" if quote.get('week52_high') else "—")
        s4.metric("52W Low",     f"${quote['week52_low']:,.2f}"  if quote.get('week52_low')  else "—")
        s1.metric("Beta",        safe(quote.get("beta")))
        s2.metric("Forward P/E", safe(quote.get("forward_pe")))
        s3.metric("EPS",         f"${quote['eps']:.2f}" if quote.get('eps') else "—")
        s4.metric("Div Yield",   f"{quote['dividend']*100:.2f}%" if quote.get('dividend') else "—")
        st.caption(f"Sector: {quote.get('sector','—')} · Industry: {quote.get('industry','—')}")


# ═══════════════════════════════════════════════════════════════════════════════
#  PAGE: MY PORTFOLIO
# ═══════════════════════════════════════════════════════════════════════════════

elif page == "My Portfolio":
    st.markdown("# My Portfolio")
    render_portfolio_page(PORTFOLIO, RETURNS_EXCLUDE, label="My Portfolio", rf=rf_rate)

    st.markdown("---")
    st.markdown("### What-If Simulator")
    st.caption("Add a hypothetical position and see how it changes your metrics.")
    wi1,wi2,wi3 = st.columns(3)
    with wi1:
        wi_ticker = st.text_input("Ticker", value="COIN", key="wi_t").upper()
        wi_qty    = st.number_input("Shares", value=10, min_value=1, key="wi_q")
    with wi2:
        wi_cost = st.number_input("Avg Cost ($)", value=200.0, step=1.0, key="wi_c")
    with wi3:
        st.markdown("<br>", unsafe_allow_html=True)
        run_wi = st.button("▶ Simulate")

    if run_wi:
        with st.spinner(f"Simulating {wi_ticker}..."):
            wi_q = get_quote(wi_ticker)
        if not wi_q or not wi_q.get("price"):
            st.error(f"Could not fetch {wi_ticker}.")
        else:
            wi_price = wi_q["price"]
            wi_val   = wi_qty * wi_price
            wi_pnl   = wi_val - (wi_qty * wi_cost)

            my_ticks = [t for t in PORTFOLIO if t not in RETURNS_EXCLUDE]
            my_qmap  = {t: get_quote(t) for t in my_ticks}
            my_total = sum(PORTFOLIO[t]["qty"] * my_qmap[t]["price"]
                          for t in my_ticks if my_qmap.get(t) and my_qmap[t].get("price"))
            my_wts   = {t: (PORTFOLIO[t]["qty"] * my_qmap[t]["price"]) / my_total
                       for t in my_ticks if my_qmap.get(t) and my_qmap[t].get("price") and my_total}

            new_total = my_total + wi_val
            new_ticks = my_ticks + [wi_ticker]
            new_wts   = {t: my_wts[t] * my_total / new_total for t in my_ticks}
            new_wts[wi_ticker] = wi_val / new_total

            with st.spinner("Computing..."):
                curr_ret = get_portfolio_returns(my_ticks, my_wts, period="1y")
                new_ret  = get_portfolio_returns(new_ticks, new_wts, period="1y")
                curr_met = compute_metrics(curr_ret, rf=rf_rate)
                new_met  = compute_metrics(new_ret,  rf=rf_rate)

            cmp1,cmp2,cmp3,cmp4 = st.columns(4)
            cmp1.metric("Position Value", f"${wi_val:,.0f}", delta=f"P&L ${wi_pnl:+,.0f}")
            cmp2.metric("New Total",      f"${new_total:,.0f}")
            if new_met and curr_met:
                cmp3.metric("Sharpe",  f"{new_met['sharpe']:.3f}",
                            delta=f"{new_met['sharpe']-curr_met['sharpe']:+.3f}")
                cmp4.metric("Ann. Vol", f"{new_met['ann_vol']:.2f}%",
                            delta=f"{new_met['ann_vol']-curr_met['ann_vol']:+.2f}%")


# ═══════════════════════════════════════════════════════════════════════════════
#  PAGE: DAD'S PORTFOLIO
# ═══════════════════════════════════════════════════════════════════════════════

elif page == "Dad's Portfolio":
    st.markdown("# Dad's Portfolio")
    st.caption("34 positions · Income & yield focused")
    render_portfolio_page(DAD_PORTFOLIO, DAD_RETURNS_EXCLUDE, label="Dad's Portfolio", rf=rf_rate)
    render_dividend_tracker(DAD_PORTFOLIO)

    # Head to head
    st.markdown("---")
    st.markdown("### Head to Head — My Portfolio vs Dad's vs SPY")
    with st.spinner("Loading comparison..."):
        my_ticks  = [t for t in PORTFOLIO if t not in RETURNS_EXCLUDE]
        my_qmap   = {t: get_quote(t) for t in my_ticks}
        my_total  = sum(PORTFOLIO[t]["qty"] * my_qmap[t]["price"]
                       for t in my_ticks if my_qmap.get(t) and my_qmap[t].get("price"))
        my_wts    = {t: (PORTFOLIO[t]["qty"] * my_qmap[t]["price"]) / my_total
                    for t in my_ticks if my_qmap.get(t) and my_qmap[t].get("price") and my_total}
        my_ret    = get_portfolio_returns(my_ticks, my_wts, period="2y")

        dad_ticks = [t for t in DAD_PORTFOLIO if t not in DAD_RETURNS_EXCLUDE]
        dad_qmap  = {t: get_quote(t) for t in dad_ticks}
        dad_total = sum(DAD_PORTFOLIO[t]["qty"] * dad_qmap[t]["price"]
                       for t in dad_ticks if dad_qmap.get(t) and dad_qmap[t].get("price"))
        dad_wts   = {t: (DAD_PORTFOLIO[t]["qty"] * dad_qmap[t]["price"]) / dad_total
                    for t in dad_ticks if dad_qmap.get(t) and dad_qmap[t].get("price") and dad_total}
        dad_ret   = get_portfolio_returns(dad_ticks, dad_wts, period="2y")

        spy_hist  = get_history("SPY", period="2y")
        spy_ret   = spy_hist["Close"].squeeze().pct_change().dropna() if not spy_hist.empty else pd.Series(dtype=float)
        my_met    = compute_metrics(my_ret,  rf=rf_rate)
        dad_met   = compute_metrics(dad_ret, rf=rf_rate)

    if my_met and dad_met:
        cmp = pd.DataFrame({
            "Metric":          ["Ann. Return","Ann. Vol","Sharpe","Sortino","Max Drawdown","Win Rate"],
            "My Portfolio":    [safe(my_met.get("ann_return"),  fmt="+.2f",suffix="%"),
                                safe(my_met.get("ann_vol"),              suffix="%"),
                                safe(my_met.get("sharpe"),     fmt=".3f"),
                                safe(my_met.get("sortino"),    fmt=".3f"),
                                safe(my_met.get("max_drawdown"),         suffix="%"),
                                safe(my_met.get("win_rate"),             suffix="%")],
            "Dad's Portfolio": [safe(dad_met.get("ann_return"), fmt="+.2f",suffix="%"),
                                safe(dad_met.get("ann_vol"),             suffix="%"),
                                safe(dad_met.get("sharpe"),    fmt=".3f"),
                                safe(dad_met.get("sortino"),   fmt=".3f"),
                                safe(dad_met.get("max_drawdown"),        suffix="%"),
                                safe(dad_met.get("win_rate"),            suffix="%")],
        })
        st.dataframe(cmp, use_container_width=True, hide_index=True)

    if not my_ret.empty and not dad_ret.empty and not spy_ret.empty:
        a_my,  a_spy  = my_ret.align(spy_ret,  join="inner")
        a_dad, a_spy2 = dad_ret.align(spy_ret, join="inner")
        a_my,  a_dad  = a_my.align(a_dad, join="inner")
        a_spy, _      = a_spy.align(a_dad, join="inner")
        st.plotly_chart(
            cumulative_returns_chart({"My Portfolio": a_my, "Dad's Portfolio": a_dad, "SPY": a_spy}),
            use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════════
#  PAGE: WATCHLIST
# ═══════════════════════════════════════════════════════════════════════════════

elif page == "Watchlist":
    st.markdown("# Watchlist")
    custom = st.text_input("Add tickers (comma-separated)", placeholder="e.g. COIN, ARM")
    watch  = list(WATCHLIST)
    if custom:
        watch += [t.strip().upper() for t in custom.split(",") if t.strip()]

    with st.spinner("Fetching quotes..."):
        quotes = get_watchlist_quotes(watch)

    valid = [q for q in quotes if q and q.get("price")]
    if not valid:
        st.warning("No quotes returned.")
    else:
        rows = [{"Ticker": q["ticker"], "Name": q["name"],
                 "Price":  f"${q['price']:,.2f}",
                 "Chg":    f"{q['chg']:+.2f}",
                 "Chg %":  f"{q['chg_pct']:+.2f}%",
                 "Volume": f"{q['volume']:,.0f}" if q.get('volume') else "—",
                 "Mkt Cap":f"${q['mkt_cap']/1e9:.1f}B" if q.get('mkt_cap') else "—",
                 "P/E":    safe(q.get("pe")),
                 "Sector": q.get("sector","—")} for q in valid]
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        st.markdown("### Sparklines (1Y)")
        cols = st.columns(4)
        for i, q in enumerate(valid[:8]):
            with cols[i % 4]:
                h = get_history(q["ticker"], period="1y")
                if not h.empty:
                    st.plotly_chart(line_chart(h, q["ticker"]), use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════════
#  PAGE: BACKTEST
# ═══════════════════════════════════════════════════════════════════════════════

elif page == "Backtest":
    st.markdown("# Backtest")
    c1,c2,c3 = st.columns(3)
    with c1:
        bt_ticker = st.selectbox("Ticker", BACKTEST_TICKERS)
        bt_period = st.selectbox("Period", ["1y","2y","3y","5y"], index=1)
    with c2:
        strategy  = st.selectbox("Strategy", ["SMA Crossover","RSI Mean Reversion","Bollinger Band","Buy & Hold"])
        init_cash = st.number_input("Initial Cash ($)", value=10_000, step=1_000)
    with c3:
        if strategy == "SMA Crossover":
            fast = st.slider("Fast MA", 5,  50,  20)
            slow = st.slider("Slow MA", 20, 200, 50)
        elif strategy == "RSI Mean Reversion":
            rsi_p  = st.slider("RSI Period", 7,  28, 14)
            os_lvl = st.slider("Oversold",   20, 40, 30)
            ob_lvl = st.slider("Overbought", 60, 80, 70)
        elif strategy == "Bollinger Band":
            bb_p   = st.slider("BB Period",  10,  40, 20)
            bb_std = st.slider("BB Std Dev", 1.0, 3.0, 2.0, 0.5)

    if st.button("▶ Run Backtest"):
        with st.spinner("Running..."):
            if strategy == "SMA Crossover":
                result = sma_crossover(bt_ticker, fast, slow, bt_period, init_cash)
            elif strategy == "RSI Mean Reversion":
                result = rsi_strategy(bt_ticker, rsi_p, os_lvl, ob_lvl, bt_period, init_cash)
            elif strategy == "Bollinger Band":
                result = bollinger_strategy(bt_ticker, bb_p, bb_std, bt_period, init_cash)
            else:
                result = buy_and_hold(bt_ticker, bt_period, init_cash)

        if "error" in result:
            st.error(result["error"])
        else:
            k1,k2,k3,k4,k5,k6 = st.columns(6)
            k1.metric("Total Return",   f"{result['total_return']:+.2f}%")
            k2.metric("Ann. Return",    f"{result['ann_return']:+.2f}%")
            k3.metric("Sharpe",         f"{result['sharpe']:.3f}")
            k4.metric("Sortino",        f"{result['sortino']:.3f}")
            k5.metric("Max Drawdown",   f"{result['max_drawdown']:.2f}%")
            k6.metric("Win Rate",       f"{result['win_rate']:.1f}%")
            k1b,k2b,k3b,k4b,k5b,k6b = st.columns(6)
            k1b.metric("Final Value",   f"${result['final_value']:,.0f}")
            k2b.metric("# Trades",      result['total_trades'])
            k3b.metric("Profit Factor", f"{result['profit_factor']:.2f}")
            k4b.metric("Expectancy",    f"${result['expectancy']:.2f}")
            k5b.metric("Calmar",        f"{result['calmar']:.3f}")
            k6b.metric("Init Cash",     f"${result['init_cash']:,.0f}")
            st.plotly_chart(equity_curve_chart(result), use_container_width=True)
            if not result["trades"].empty:
                st.markdown("### Trade Log")
                st.dataframe(result["trades"].head(50), use_container_width=True, hide_index=True)

    st.markdown("---")
    st.markdown("### SMA Parameter Sweep")
    sweep_ticker = st.selectbox("Ticker", BACKTEST_TICKERS, key="sweep_t")
    if st.button("▶ Run Sweep"):
        with st.spinner("Sweeping (~30s)..."):
            pivot = sma_sweep(sweep_ticker, period="2y")
        if not pivot.empty:
            st.plotly_chart(sma_heatmap(pivot, sweep_ticker), use_container_width=True)
        else:
            st.warning("No results.")


# ═══════════════════════════════════════════════════════════════════════════════
#  PAGE: OPTIMISER
# ═══════════════════════════════════════════════════════════════════════════════

elif page == "Optimiser":
    st.markdown("# Portfolio Optimiser")
    c1,c2,c3 = st.columns(3)
    with c1:
        opt_tickers = st.multiselect("Universe", OPTIMISER_TICKERS, default=OPTIMISER_TICKERS)
        opt_period  = st.selectbox("History", ["1y","2y","3y","5y"], index=1)
    with c2:
        method_map = {"max_sharpe":"Maximise Sharpe","min_volatility":"Minimise Volatility",
                      "efficient_return":"Target Return","efficient_risk":"Target Risk"}
        opt_method = st.selectbox("Objective", list(method_map.keys()), format_func=lambda k: method_map[k])
    with c3:
        target_return = st.number_input("Target Return (%)", value=15.0, step=1.0) if opt_method=="efficient_return" else None
        target_risk   = st.number_input("Target Risk (%)",   value=15.0, step=1.0) if opt_method=="efficient_risk"   else None
        portfolio_val = st.number_input("Portfolio Value ($)", value=50_000, step=1_000)

    if st.button("▶ Optimise"):
        if len(opt_tickers) < 2:
            st.warning("Select at least 2 tickers.")
        else:
            with st.spinner("Running..."):
                res = run_optimisation(opt_tickers, period=opt_period, rf=rf_rate,
                                       method=opt_method, target_return=target_return, target_risk=target_risk)
            if "error" in res:
                st.error(res["error"])
            else:
                p1,p2,p3 = st.columns(3)
                p1.metric("Expected Return",     f"{res['exp_return']:.2f}%")
                p2.metric("Expected Volatility", f"{res['exp_volatility']:.2f}%")
                p3.metric("Sharpe",              f"{res['sharpe']:.3f}")
                st.markdown("---")
                c1,c2 = st.columns(2)
                with c1:
                    st.plotly_chart(weights_bar(res["weights"]), use_container_width=True)
                with c2:
                    with st.spinner("Building frontier..."):
                        frontier = efficient_frontier_curve(res["mu"], res["S"], rf=rf_rate)
                    if not frontier.empty:
                        st.plotly_chart(efficient_frontier_chart(frontier, res["exp_volatility"],
                                                                  res["exp_return"], res["sharpe"]),
                                        use_container_width=True)
                st.markdown("### Optimal Weights")
                w_df = pd.DataFrame([{"Ticker":k,"Weight":f"{v*100:.2f}%"}
                                     for k,v in res["weights"].items() if v > 0.001])
                st.dataframe(w_df, use_container_width=True, hide_index=True)
                st.markdown("### Share Allocation")
                alloc    = discrete_allocation(res["weights"], res["tickers"], res["closes"], portfolio_val)
                alloc_df = pd.DataFrame([{"Ticker":k,"Shares":v} for k,v in alloc["allocation"].items()])
                st.dataframe(alloc_df, use_container_width=True, hide_index=True)
                st.caption(f"Leftover cash: ${alloc['leftover']:,.2f}")
                with st.spinner("Computing correlation..."):
                    corr = correlation_matrix(res["tickers"], period=opt_period)
                if not corr.empty:
                    st.plotly_chart(correlation_heatmap(corr), use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════════
#  PAGE: RESEARCH — Live SEC EDGAR Fundamentals
# ═══════════════════════════════════════════════════════════════════════════════

elif page == "Research":
    from data.sec_fetcher import get_financials, get_recent_filings
    from charts.research_plots import (fmt_b, revenue_bar, net_income_bar, margin_trend,
                                        eps_chart, rd_bar, revenue_vs_income)

    st.markdown("# Research")
    st.caption("Live fundamental data pulled directly from SEC EDGAR filings — updates automatically when new 10-K or 10-Q is filed.")

    # Ticker selector
    research_tickers = list(PORTFOLIO.keys()) + ["MSFT", "AMZN", "GOOGL", "META"]
    research_tickers = [t for t in research_tickers if t not in ["STRK", "MSTR"]]

    c1, c2 = st.columns([2, 1])
    with c1:
        sel_ticker = st.selectbox("Select Company", research_tickers, key="res_ticker")
    with c2:
        period = st.radio("Period", ["Annual", "Quarterly"], horizontal=True, key="res_period")

    with st.spinner(f"Fetching SEC filings for {sel_ticker}..."):
        fin = get_financials(sel_ticker)
        filings = get_recent_filings(sel_ticker)

    if not fin:
        st.error(f"Could not fetch SEC data for {sel_ticker}. Try another ticker.")
    else:
        # Header
        st.markdown(f"## {fin['name']}")
        if fin.get("filing_date"):
            st.caption(f"Latest 10-K filed: {fin['filing_date']} · Source: SEC EDGAR · Auto-updates on new filing")

        st.markdown("---")

        # Key metrics
        st.markdown("### Key Financials")
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Revenue",      fmt_b(fin.get("revenue")))
        m2.metric("Net Income",   fmt_b(fin.get("net_income")))
        m3.metric("Gross Profit", fmt_b(fin.get("gross_profit")))
        m4.metric("Gross Margin", f"{fin['gross_margin']:.1f}%" if fin.get("gross_margin") else "—")
        m5.metric("Cash",         fmt_b(fin.get("cash")))

        st.markdown("---")

        # Charts — row 1
        c1, c2 = st.columns(2)
        with c1:
            rev_df = fin["rev_annual"] if period == "Annual" else fin["rev_quarterly"]
            if not rev_df.empty:
                st.plotly_chart(revenue_bar(rev_df, sel_ticker, period), use_container_width=True)
            else:
                st.info("Revenue data not available.")

        with c2:
            if not fin["net_annual"].empty:
                st.plotly_chart(net_income_bar(fin["net_annual"], sel_ticker), use_container_width=True)
            else:
                st.info("Net income data not available.")

        # Charts — row 2
        c3, c4 = st.columns(2)
        with c3:
            if not fin["rev_annual"].empty and not fin["gp_annual"].empty:
                st.plotly_chart(margin_trend(fin["rev_annual"], fin["gp_annual"], sel_ticker), use_container_width=True)
            else:
                st.info("Margin data not available.")

        with c4:
            if not fin["eps_quarterly"].empty:
                st.plotly_chart(eps_chart(fin["eps_quarterly"], sel_ticker), use_container_width=True)
            else:
                st.info("EPS data not available.")

        # Charts — row 3
        c5, c6 = st.columns(2)
        with c5:
            if not fin["rev_annual"].empty and not fin["net_annual"].empty:
                st.plotly_chart(revenue_vs_income(fin["rev_annual"], fin["net_annual"], sel_ticker), use_container_width=True)
        with c6:
            if not fin["rd_annual"].empty:
                st.plotly_chart(rd_bar(fin["rd_annual"], sel_ticker), use_container_width=True)
            else:
                st.info("R&D data not available.")

        # Recent filings table
        st.markdown("---")
        st.markdown("### Recent SEC Filings")
        if filings:
            for f in filings:
                col1, col2, col3 = st.columns([1, 2, 2])
                col1.markdown(f"**{f['form']}**")
                col2.markdown(f"{f['date']}")
                col3.markdown(f"[View on EDGAR ↗]({f['url']})")
        else:
            st.info("No recent filings found.")

        st.markdown("---")
        st.caption("Data sourced directly from SEC EDGAR XBRL API · Free, no API key required · Updates within hours of new filing · Not financial advice")
