"""
data/sec_fetcher.py
SEC EDGAR API — pulls real 10-K/10-Q data for any ticker.
No API key needed — EDGAR is free and public.
"""

import requests
import pandas as pd
import streamlit as st

EDGAR_BASE = "https://data.sec.gov/api/xbrl/companyfacts"
HEADERS    = {"User-Agent": "InvestingVisuals research@investingvisuals.com"}

CIK_MAP = {
    "AAPL": "0000320193",
    "NVDA": "0001045810",
    "TSLA": "0001318605",
    "MSFT": "0000789019",
    "AMZN": "0001018724",
    "GOOGL": "0001652044",
    "META":  "0001326801",
    "AMD":   "0000002488",
    "INTC":  "0000050863",
    "QCOM":  "0000804328",
}


@st.cache_data(ttl=3600*6, show_spinner=False)
def get_company_facts(ticker: str) -> dict:
    cik = CIK_MAP.get(ticker.upper(), "")
    if not cik:
        return {}
    try:
        cik_padded = cik.lstrip("0").zfill(10)
        r = requests.get(f"{EDGAR_BASE}/CIK{cik_padded}.json",
                         headers=HEADERS, timeout=15)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return {}


def extract_metric(facts: dict, concept: str, unit: str = "USD") -> pd.DataFrame:
    try:
        data  = facts.get("facts", {}).get("us-gaap", {}).get(concept, {})
        units = data.get("units", {}).get(unit, [])
        if not units:
            return pd.DataFrame()
        df = pd.DataFrame(units)
        df = df[df["form"].isin(["10-K", "10-K405", "10-KSB", "10-Q"])].copy()
        df["end"] = pd.to_datetime(df["end"])
        return df.sort_values("end", ascending=False)
    except Exception:
        return pd.DataFrame()


def _annual(df: pd.DataFrame, n: int = 15) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    a = df[df["form"].isin(["10-K","10-K405","10-KSB"])].drop_duplicates(subset=["end"]).head(n)
    return a[["end","val"]].sort_values("end")


def _quarterly(df: pd.DataFrame, n: int = 40) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    q = df[df["form"] == "10-Q"].drop_duplicates(subset=["end"]).head(n)
    return q[["end","val"]].sort_values("end")


def _latest_annual(df: pd.DataFrame):
    if df.empty:
        return None
    a = df[df["form"].isin(["10-K","10-K405","10-KSB"])]
    return a.iloc[0] if not a.empty else None


@st.cache_data(ttl=3600*6, show_spinner=False)
def get_financials(ticker: str) -> dict:
    facts = get_company_facts(ticker)
    if not facts:
        return {}

    name = facts.get("entityName", ticker)

    # ── Fetch all metrics ─────────────────────────────────────────────────────
    rev = extract_metric(facts, "Revenues")
    if rev.empty:
        rev = extract_metric(facts, "RevenueFromContractWithCustomerExcludingAssessedTax")
    if rev.empty:
        rev = extract_metric(facts, "SalesRevenueNet")

    net   = extract_metric(facts, "NetIncomeLoss")
    gp    = extract_metric(facts, "GrossProfit")
    op    = extract_metric(facts, "OperatingIncomeLoss")
    rd    = extract_metric(facts, "ResearchAndDevelopmentExpense")
    eps   = extract_metric(facts, "EarningsPerShareBasic", unit="USD/shares")
    assets= extract_metric(facts, "Assets")

    # Cash
    cash = extract_metric(facts, "CashCashEquivalentsAndShortTermInvestments")
    if cash.empty:
        cash = extract_metric(facts, "CashAndCashEquivalentsAtCarryingValue")

    # Free Cash Flow components
    op_cf  = extract_metric(facts, "NetCashProvidedByUsedInOperatingActivities")
    capex  = extract_metric(facts, "PaymentsToAcquirePropertyPlantAndEquipment")

    # Debt
    ltd    = extract_metric(facts, "LongTermDebt")
    std    = extract_metric(facts, "ShortTermBorrowings")

    # Shares outstanding
    shares = extract_metric(facts, "CommonStockSharesOutstanding", unit="shares")

    # ── Latest annual values ──────────────────────────────────────────────────
    la_rev    = _latest_annual(rev)
    la_net    = _latest_annual(net)
    la_gp     = _latest_annual(gp)
    la_op     = _latest_annual(op)
    la_assets = _latest_annual(assets)
    la_cash   = _latest_annual(cash)
    la_op_cf  = _latest_annual(op_cf)
    la_capex  = _latest_annual(capex)
    la_ltd    = _latest_annual(ltd)
    la_shares = _latest_annual(shares)

    # Computed metrics
    gross_margin = None
    if la_rev is not None and la_gp is not None and la_rev["val"]:
        gross_margin = round(la_gp["val"] / la_rev["val"] * 100, 1)

    op_margin = None
    if la_rev is not None and la_op is not None and la_rev["val"]:
        op_margin = round(la_op["val"] / la_rev["val"] * 100, 1)

    net_margin = None
    if la_rev is not None and la_net is not None and la_rev["val"]:
        net_margin = round(la_net["val"] / la_rev["val"] * 100, 1)

    fcf = None
    if la_op_cf is not None and la_capex is not None:
        fcf = la_op_cf["val"] - la_capex["val"]

    filing_date = la_rev.get("filed", "") if la_rev is not None else ""

    # ── Annual series (for charts) ────────────────────────────────────────────
    rev_a   = _annual(rev)
    net_a   = _annual(net)
    gp_a    = _annual(gp)
    op_a    = _annual(op)
    rd_a    = _annual(rd)
    cash_a  = _annual(cash) if not _annual(cash).empty else _quarterly(cash, 8)
    op_cf_a = _annual(op_cf)
    capex_a = _annual(capex)

    # FCF annual series
    fcf_a = pd.DataFrame()
    if not op_cf_a.empty and not capex_a.empty:
        merged = op_cf_a.merge(capex_a, on="end", suffixes=("_ocf","_cx"))
        merged["val"] = merged["val_ocf"] - merged["val_cx"]
        fcf_a = merged[["end","val"]]

    # YoY growth on revenue
    rev_growth_a = pd.DataFrame()
    if len(rev_a) >= 2:
        rev_growth_a = rev_a.copy()
        rev_growth_a["val"] = rev_a["val"].pct_change() * 100
        rev_growth_a = rev_growth_a.dropna()

    # ── Quarterly series ──────────────────────────────────────────────────────
    rev_q   = _quarterly(rev)
    net_q   = _quarterly(net)
    gp_q    = _quarterly(gp)
    rd_q    = _quarterly(rd)
    cash_q  = _quarterly(cash)
    eps_q   = _quarterly(eps, unit="USD/shares") if False else extract_metric(facts, "EarningsPerShareBasic", unit="USD/shares")
    eps_q   = _quarterly(eps_q) if not eps_q.empty else pd.DataFrame()

    # Quarterly revenue growth
    rev_growth_q = pd.DataFrame()
    if len(rev_q) >= 2:
        rev_growth_q = rev_q.copy()
        rev_growth_q["val"] = rev_q["val"].pct_change() * 100
        rev_growth_q = rev_growth_q.dropna()

    return {
        # Metadata
        "ticker":       ticker,
        "name":         name,
        "filing_date":  filing_date,
        # Latest scalars
        "revenue":      la_rev["val"]    if la_rev    is not None else None,
        "net_income":   la_net["val"]    if la_net    is not None else None,
        "gross_profit": la_gp["val"]     if la_gp     is not None else None,
        "op_income":    la_op["val"]     if la_op     is not None else None,
        "gross_margin": gross_margin,
        "op_margin":    op_margin,
        "net_margin":   net_margin,
        "total_assets": la_assets["val"] if la_assets is not None else None,
        "cash":         la_cash["val"]   if la_cash   is not None else None,
        "fcf":          fcf,
        "long_term_debt": la_ltd["val"]  if la_ltd    is not None else None,
        "shares":       la_shares["val"] if la_shares is not None else None,
        # Annual series
        "rev_annual":        rev_a,
        "net_annual":        net_a,
        "gp_annual":         gp_a,
        "op_annual":         op_a,
        "rd_annual":         rd_a,
        "cash_annual":       cash_a,
        "fcf_annual":        fcf_a,
        "rev_growth_annual": rev_growth_a,
        # Quarterly series
        "rev_quarterly":        rev_q,
        "net_quarterly":        net_q,
        "gp_quarterly":         gp_q,
        "rd_quarterly":         rd_q,
        "cash_quarterly":       cash_q,
        "eps_quarterly":        eps_q,
        "rev_growth_quarterly": rev_growth_q,
    }


@st.cache_data(ttl=3600*6, show_spinner=False)
def get_recent_filings(ticker: str, n: int = 5) -> list:
    cik = CIK_MAP.get(ticker.upper(), "")
    if not cik:
        return []
    try:
        cik_padded = cik.lstrip("0").zfill(10)
        r = requests.get(
            f"https://data.sec.gov/submissions/CIK{cik_padded}.json",
            headers=HEADERS, timeout=10)
        data    = r.json()
        filings = data.get("filings", {}).get("recent", {})
        forms   = filings.get("form", [])
        dates   = filings.get("filingDate", [])
        results = []
        for form, date in zip(forms, dates):
            if form in ["10-K", "10-Q"] and len(results) < n:
                results.append({"form": form, "date": date,
                    "url": f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik_padded}&type={form}&dateb=&owner=include&count=10"})
        return results
    except Exception:
        return []


def fmt_b(val):
    if val is None:
        return "—"
    b = val / 1e9
    if abs(b) >= 1000:
        return f"${b/1000:.1f}T"
    return f"${b:.1f}B"
