"""Daily market scan using yfinance.

This is a read-only research tool. It fetches recent daily closes, computes
day-over-day % change, and flags symbols that moved >= 3%. Network/parse
failures are caught by the caller so automation does not break on a bad fetch.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

import yfinance as yf

# Default watchlist: AI/semis core book + regime indices + macro/hedge tickers.
DEFAULT_WATCHLIST = [
    "NVDA", "AVGO", "VRT", "MU", "SMCI", "AMD", "INTC", "TSM", "ASML", "ARM",
    "MSFT", "META", "GOOGL", "AMZN", "AAPL", "PLTR", "SNOW", "CRWD", "NET", "ORCL",
    "SPY", "QQQ", "SMH", "GLD", "TLT", "IEF", "SHY", "GDXJ", "USO", "BTC-USD",
]


def _pct(prev: float, last: float) -> Optional[float]:
    if not prev:
        return None
    return (last - prev) / prev * 100.0


def run_scan(
    date_str: Optional[str] = None,
    tickers: Optional[list[str]] = None,
    period: str = "5d",
):
    """Return (as_of_date, rows) where each row is (symbol, price, pct, status)."""
    tickers = list(tickers) if tickers else list(DEFAULT_WATCHLIST)
    as_of = datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else datetime.now().date()
    rows: list[tuple[str, Optional[float], Optional[float], str]] = []
    for sym in tickers:
        try:
            df = yf.download(sym, period=period, interval="1d", progress=False, auto_adjust=True)
            if df is None or df.empty or "Close" not in df.columns:
                rows.append((sym, None, None, "no-data"))
                continue
            close = df["Close"].dropna()
            if len(close) < 2:
                rows.append((sym, float(close.iloc[-1]), None, "insufficient"))
                continue
            last = float(close.iloc[-1])
            prev = float(close.iloc[-2])
            rows.append((sym, last, _pct(prev, last), "ok"))
        except Exception as exc:  # noqa: BLE001 - network/parse errors are expected
            rows.append((sym, None, None, f"err:{type(exc).__name__}"))
    return as_of, rows
