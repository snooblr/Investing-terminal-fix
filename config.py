# ─────────────────────────────────────────────
#  TERMINAL CONFIG
# ─────────────────────────────────────────────

CACHE_TTL = 15

# ── Your Watchlist ────────────────────────────
WATCHLIST = ["SPY", "QQQ", "NVDA", "TSLA", "AAPL", "MSTR", "STRK", "GLD", "BTC-USD"]

# ── Your Portfolio ────────────────────────────
PORTFOLIO = {
    "NVDA":  {"qty": 10, "avg_cost": 27.19},
    "TSLA":  {"qty": 7,  "avg_cost": 267.65},
    "AAPL":  {"qty": 3,  "avg_cost": 163.55},
    "MSTR":  {"qty": 5,  "avg_cost": 320.00},
    "STRK":  {"qty": 4,  "avg_cost": 95.00},
}

# Tickers excluded from returns/risk chart (too new or illiquid)
RETURNS_EXCLUDE = ["STRK", "MSTR"]

# ── Backtest universe ─────────────────────────
BACKTEST_TICKERS = ["NVDA", "TSLA", "AAPL", "SPY", "QQQ"]

# ── Optimiser universe ────────────────────────
OPTIMISER_TICKERS = ["NVDA", "TSLA", "AAPL", "SPY", "QQQ", "AMZN", "MSFT", "GLD"]

# ── Dad's Portfolio ───────────────────────────
DAD_PORTFOLIO = {
    "ACHR":  {"qty": 400, "avg_cost": 8.87},
    "AMDY":  {"qty": 4,   "avg_cost": 54.10},
    "BP":    {"qty": 20,  "avg_cost": 37.17},
    "CAG":   {"qty": 100, "avg_cost": 17.94},
    "CLNE":  {"qty": 60,  "avg_cost": 5.03},
    "CMCSA": {"qty": 15,  "avg_cost": 29.83},
    "CRON":  {"qty": 60,  "avg_cost": 4.45},
    "F":     {"qty": 15,  "avg_cost": 10.95},
    "JBLU":  {"qty": 300, "avg_cost": 5.65},
    "JBND":  {"qty": 30,  "avg_cost": 54.22},
    "JEPI":  {"qty": 30,  "avg_cost": 56.59},
    "JEPQ":  {"qty": 40,  "avg_cost": 55.23},
    "KHC":   {"qty": 100, "avg_cost": 23.98},
    "NVDY":  {"qty": 8,   "avg_cost": 13.13},
    "PFE":   {"qty": 100, "avg_cost": 25.75},
    "QQQI":  {"qty": 20,  "avg_cost": 53.08},
    "SCHD":  {"qty": 100, "avg_cost": 25.24},
    "SCHF":  {"qty": 2,   "avg_cost": 23.63},
    "SCHO":  {"qty": 10,  "avg_cost": 24.31},
    "SCHP":  {"qty": 100, "avg_cost": 26.86},
    "SPYI":  {"qty": 23,  "avg_cost": 51.11},
    "STRC":  {"qty": 10,  "avg_cost": 99.09},
    "STRK":  {"qty": 17,  "avg_cost": 90.38},
    "T":     {"qty": 30,  "avg_cost": 24.28},
    "TLT":   {"qty": 30,  "avg_cost": 84.46},
    "TSLA":  {"qty": 2,   "avg_cost": 409.25},
    "TSLY":  {"qty": 5,   "avg_cost": 0.00},
    "UPS":   {"qty": 25,  "avg_cost": 92.98},
    "UWMC":  {"qty": 100, "avg_cost": 4.89},
    "VTIP":  {"qty": 15,  "avg_cost": 49.73},
    "XTIA":  {"qty": 10,  "avg_cost": 2.50},
    "SWPPX": {"qty": 17,  "avg_cost": 17.60},
    "SWRSX": {"qty": 48,  "avg_cost": 10.34},
    "SWTSX": {"qty": 12,  "avg_cost": 16.39},
    "LCID":  {"qty": 10,  "avg_cost": 61.60},
}

# Tickers excluded from dad's returns chart (too new/illiquid)
DAD_RETURNS_EXCLUDE = [
    "STRK", "STRC", "TSLY", "XTIA", "AMDY", "CLNE", "CRON",
    "ACHR", "LCID", "UWMC", "JBLU", "NVDY", "QQQI", "SPYI",
    "SWRSX", "SWTSX", "SWPPX", "VTIP", "SCHO", "SCHP", "SCHF",
]

# ── Investing Visuals theme ───────────────────
IV_THEME = {
    "bg":           "#f2ede4",
    "bg2":          "#e8e2d6",
    "ink":          "#111111",
    "ink_mid":      "#444444",
    "ink_muted":    "#888888",
    "s1":           "#1a1a1a",
    "s2":           "#5a5a5a",
    "s3":           "#a0a0a0",
    "s4":           "#c8c8c8",
    "green":        "#2d6a2d",
    "red":          "#8b2020",
    "green_bg":     "#e8f0e8",
    "red_bg":       "#f0e8e8",
    "font_display": "Playfair Display, Georgia, serif",
    "font_body":    "DM Sans, sans-serif",
}
