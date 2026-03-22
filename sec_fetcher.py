"""
data/sec_fetcher.py
SEC EDGAR API — pulls real 10-K/10-Q data for any ticker.
No API key needed — EDGAR is free and public.
"""

import requests
import pandas as pd
import streamlit as st
from datetime import datetime

EDGAR_BASE    = "https://data.sec.gov/api/xbrl/companyfacts"
EDGAR_SEARCH  = "https://efts.sec.gov/LATEST/search-index?q=%22{ticker}%22&dateRange=custom&startdt=2020-01-01&forms=10-K,10-Q"
HEADERS       = {"User-Agent": "InvestingVisuals research@investingvisuals.com"}

# Ticker → CIK mapping (SEC uses CIK not ticker)
CIK_MAP = {
    "AAPL": "0000320193",
    "NVDA": "0001045810",
    "TSLA": "0001318605",
    "MSFT": "0000789019",
    "AMZN": "0001018724",
    "GOOGL": "0001652044",
    "META": "0001326801",
    "SPY":  None,
}


@st.cache_data(ttl=3600*6, show_spinner=False)
def get_cik(ticker: str) -> str:
    """Get CIK from ticker via EDGAR company search."""
    if ticker in CIK_MAP and CIK_MAP[ticker]:
        return CIK_MAP[ticker]
    try:
        r = requests.get(
            f"https://efts.sec.gov/LATEST/search-index?q=%22{ticker}%22&forms=10-K",
            headers=HEADERS, timeout=10)
        data = r.json()
        hits = data.get("hits", {}).get("hits", [])
        if hits:
            return hits[0].get("_source", {}).get("entity_id", "")
    except Exception:
        pass
    return ""


@st.cache_data(ttl=3600*6, show_spinner=False)
def get_company_facts(ticker: str) -> dict:
    """Pull all XBRL facts for a company from EDGAR."""
    cik = get_cik(ticker)
    if not cik:
        return {}
    try:
        cik_padded = str(cik).lstrip("0").zfill(10)
        r = requests.get(f"{EDGAR_BASE}/CIK{cik_padded}.json",
                         headers=HEADERS, timeout=15)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return {}


def extract_metric(facts: dict, concept: str, unit: str = "USD",
                   taxonomy: str = "us-gaap") -> pd.DataFrame:
    """Extract a specific financial metric as a DataFrame."""
    try:
        data = facts.get("facts", {}).get(taxonomy, {}).get(concept, {})
        units = data.get("units", {}).get(unit, [])
        if not units:
            return pd.DataFrame()
        df = pd.DataFrame(units)
        df = df[df["form"].isin(["10-K", "10-Q"])].copy()
        df["end"] = pd.to_datetime(df["end"])
        df = df.sort_values("end", ascending=False)
        return df
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=3600*6, show_spinner=False)
def get_financials(ticker: str) -> dict:
    """
    Pull key financial metrics for a ticker.
    Returns dict with DataFrames for each metric.
    """
    facts = get_company_facts(ticker)
    if not facts:
        return {}

    name = facts.get("entityName", ticker)

    # Revenue
    rev = extract_metric(facts, "Revenues")
    if rev.empty:
        rev = extract_metric(facts, "RevenueFromContractWithCustomerExcludingAssessedTax")
    if rev.empty:
        rev = extract_metric(facts, "SalesRevenueNet")

    # Net Income
    net = extract_metric(facts, "NetIncomeLoss")

    # Gross Profit
    gp = extract_metric(facts, "GrossProfit")

    # Operating Income
    op = extract_metric(facts, "OperatingIncomeLoss")

    # R&D
    rd = extract_metric(facts, "ResearchAndDevelopmentExpense")

    # EPS
    eps = extract_metric(facts, "EarningsPerShareBasic", unit="USD/shares")

    # Shares outstanding
    shares = extract_metric(facts, "CommonStockSharesOutstanding", unit="shares")

    # Total Assets
    assets = extract_metric(facts, "Assets")

    # Cash
    cash = extract_metric(facts, "CashAndCashEquivalentsAtCarryingValue")

    def latest_annual(df):
        """Get the most recent annual (10-K) figure."""
        if df.empty:
            return None
        annual = df[df["form"] == "10-K"]
        if annual.empty:
            return None
        return annual.iloc[0]

    def quarterly_series(df, n=8):
        """Get last N quarterly figures."""
        if df.empty:
            return pd.DataFrame()
        q = df[df["form"] == "10-Q"].drop_duplicates(subset=["end"]).head(n)
        return q[["end", "val"]].sort_values("end")

    def annual_series(df, n=4):
        """Get last N annual figures."""
        if df.empty:
            return pd.DataFrame()
        a = df[df["form"] == "10-K"].drop_duplicates(subset=["end"]).head(n)
        return a[["end", "val"]].sort_values("end")

    # Latest filing info
    latest_rev    = latest_annual(rev)
    latest_net    = latest_annual(net)
    latest_gp     = latest_annual(gp)
    latest_op     = latest_annual(op)
    latest_assets = latest_annual(assets)
    latest_cash   = latest_annual(cash)

    # Gross margin
    gross_margin = None
    if latest_rev is not None and latest_gp is not None:
        r_val = latest_rev["val"]
        g_val = latest_gp["val"]
        if r_val:
            gross_margin = round(g_val / r_val * 100, 1)

    # Filing date
    filing_date = None
    if latest_rev is not None:
        filing_date = latest_rev.get("filed", "")

    return {
        "ticker":         ticker,
        "name":           name,
        "filing_date":    filing_date,
        "revenue":        latest_rev["val"] if latest_rev is not None else None,
        "net_income":     latest_net["val"] if latest_net is not None else None,
        "gross_profit":   latest_gp["val"]  if latest_gp  is not None else None,
        "op_income":      latest_op["val"]  if latest_op  is not None else None,
        "gross_margin":   gross_margin,
        "total_assets":   latest_assets["val"] if latest_assets is not None else None,
        "cash":           latest_cash["val"]   if latest_cash   is not None else None,
        "rev_annual":     annual_series(rev),
        "rev_quarterly":  quarterly_series(rev),
        "net_annual":     annual_series(net),
        "net_quarterly":  quarterly_series(net),
        "gp_annual":      annual_series(gp),
        "op_annual":      annual_series(op),
        "rd_annual":      annual_series(rd),
        "eps_quarterly":  quarterly_series(eps),
    }


@st.cache_data(ttl=3600*6, show_spinner=False)
def get_recent_filings(ticker: str, n: int = 5) -> list:
    """Get most recent 10-K and 10-Q filings for a ticker."""
    cik = get_cik(ticker)
    if not cik:
        return []
    try:
        cik_padded = str(cik).lstrip("0").zfill(10)
        r = requests.get(
            f"https://data.sec.gov/submissions/CIK{cik_padded}.json",
            headers=HEADERS, timeout=10)
        data = r.json()
        filings = data.get("filings", {}).get("recent", {})
        forms   = filings.get("form", [])
        dates   = filings.get("filingDate", [])
        docs    = filings.get("primaryDocument", [])
        accnums = filings.get("accessionNumber", [])

        results = []
        for form, date, doc, acc in zip(forms, dates, docs, accnums):
            if form in ["10-K", "10-Q"] and len(results) < n:
                acc_fmt = acc.replace("-", "")
                url = f"https://www.sec.gov/Archives/edgar/full-index/{acc_fmt[:4]}/{acc_fmt[4:6]}/{acc_fmt[6:8]}/{acc}/{doc}"
                results.append({
                    "form": form,
                    "date": date,
                    "url":  f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik_padded}&type={form}&dateb=&owner=include&count=10",
                })
        return results
    except Exception:
        return []
