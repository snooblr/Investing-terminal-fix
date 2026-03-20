"""
data/fetcher.py — yfinance + Alpha Vantage dividend data
"""

import time
import requests
import yfinance as yf
import pandas as pd
import streamlit as st
from config import CACHE_TTL

AV_KEY  = "GAMWJOKIFEQ94I69"
AV_BASE = "https://www.alphavantage.co/query"


def _download_with_retry(ticker, period, interval, retries=3):
    for i in range(retries):
        try:
            df = yf.download(ticker, period=period, interval=interval,
                             auto_adjust=True, progress=False)
            df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
            if not df.empty:
                return df
            time.sleep(1)
        except Exception:
            time.sleep(1)
    return pd.DataFrame()


@st.cache_data(ttl=CACHE_TTL * 60, show_spinner=False)
def get_history(ticker: str, period: str = "1y", interval: str = "1d") -> pd.DataFrame:
    return _download_with_retry(ticker, period, interval)


@st.cache_data(ttl=CACHE_TTL * 60, show_spinner=False)
def get_multi_history(tickers: list, period: str = "1y", interval: str = "1d") -> pd.DataFrame:
    try:
        raw = yf.download(tickers, period=period, interval=interval,
                          auto_adjust=True, progress=False)
        if isinstance(raw.columns, pd.MultiIndex):
            closes = raw["Close"]
        else:
            closes = raw[["Close"]]
            closes.columns = tickers
        return closes.dropna(how="all")
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=CACHE_TTL * 60, show_spinner=False)
def get_quote(ticker: str) -> dict:
    for attempt in range(3):
        try:
            t    = yf.Ticker(ticker)
            info = t.info
            hist = _download_with_retry(ticker, "5d", "1d")
            if len(hist) >= 2:
                prev_close = float(hist["Close"].iloc[-2])
                last_price = float(hist["Close"].iloc[-1])
            elif len(hist) == 1:
                prev_close = float(info.get("previousClose") or hist["Close"].iloc[0])
                last_price = float(hist["Close"].iloc[0])
            else:
                prev_close = float(info.get("previousClose") or info.get("regularMarketPreviousClose") or 0)
                last_price = float(info.get("currentPrice") or info.get("regularMarketPrice") or 0)
            if last_price == 0:
                time.sleep(1)
                continue
            chg     = last_price - prev_close
            chg_pct = (chg / prev_close * 100) if prev_close else 0
            return {
                "ticker":      ticker,
                "name":        info.get("shortName", ticker),
                "price":       round(last_price, 2),
                "prev_close":  round(prev_close, 2),
                "chg":         round(chg, 2),
                "chg_pct":     round(chg_pct, 2),
                "volume":      info.get("volume", 0),
                "avg_volume":  info.get("averageVolume", 0),
                "mkt_cap":     info.get("marketCap", 0),
                "pe":          info.get("trailingPE"),
                "forward_pe":  info.get("forwardPE"),
                "eps":         info.get("trailingEps"),
                "beta":        info.get("beta"),
                "week52_high": info.get("fiftyTwoWeekHigh"),
                "week52_low":  info.get("fiftyTwoWeekLow"),
                "sector":      info.get("sector", "—"),
                "industry":    info.get("industry", "—"),
                "dividend":    info.get("dividendYield"),
            }
        except Exception:
            time.sleep(1)
    return {}


@st.cache_data(ttl=CACHE_TTL * 60, show_spinner=False)
def get_watchlist_quotes(tickers: list) -> list:
    return [get_quote(t) for t in tickers]


@st.cache_data(ttl=60, show_spinner=False)
def get_intraday(ticker: str) -> pd.DataFrame:
    return _download_with_retry(ticker, "1d", "5m")


@st.cache_data(ttl=3600, show_spinner=False)
def get_dividend_data(ticker: str) -> dict:
    try:
        r = requests.get(AV_BASE,
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
