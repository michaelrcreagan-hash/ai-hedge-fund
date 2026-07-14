"""Command-line interface for the AI Hedge Fund system (read-only research scan).

Lightweight, read-only research/scan toolkit. Does NOT place trades; live
execution lives in main.py / src/orchestrator.py (BottleneckFundOrchestrator).

Subcommands: status, snapshot, scan, rebalance, backtest, monte-carlo.
`scan` uses yfinance only and degrades gracefully so scheduled CI stays green.
"""
from __future__ import annotations

import argparse
import os
import sys
import datetime as _dt
from datetime import datetime, timezone
from pathlib import Path

import yaml

try:
    import yfinance as yf
except Exception:  # pragma: no cover - optional at runtime
    yf = None

CONFIG_PATH = Path(__file__).resolve().parents[2] / "config.yaml"

API_KEY_ENV = [
    "TIPRANKS_API_KEY",
    "LSEG_API_KEY",
    "FINNHUB_API_KEY",
    "OPENAI_API_KEY",
    "POLYMARKET_API_KEY",
    "FRED_API_KEY",
]


def load_config() -> dict:
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r", encoding="utf-8") as fh:
            return yaml.safe_load(fh) or {}
    return {}


def universe(config: dict) -> list:
    uni = config.get("universe", {})
    tickers = []
    tickers.extend(uni.get("indices", []))
    tickers.extend(uni.get("hedge_tickers", []))
    return tickers


def cmd_status(args: argparse.Namespace) -> int:
    config = load_config()
    keys = {k: bool(os.environ.get(k)) for k in API_KEY_ENV}
    print("=== AI Hedge Fund :: System Status ===")
    print(f"  time (UTC)    : {datetime.now(timezone.utc).isoformat(timespec='seconds')}")
    print(f"  local time    : {_dt.datetime.now().isoformat(timespec='seconds')}")
    print(f"  config loaded : {'yes' if config else 'no'}")
    print(f"  universe size : {len(universe(config))} tickers")
    print("  api keys      :")
    for k, present in keys.items():
        print(f"    - {k:20} {'SET' if present else 'missing'}")
    return 0


def cmd_snapshot(args: argparse.Namespace) -> int:
    config = load_config()
    uni = config.get("universe", {})
    print("=== Portfolio Snapshot ===")
    print(f"  version      : {uni.get('version', '?')}")
    print(f"  total_stocks : {uni.get('total_stocks', '?')}")
    print("  sleeves (risk_on allocation):")
    for sleeve, frac in config.get("risk_on", {}).items():
        print(f"    - {sleeve:12} {frac}")
    return 0


def cmd_scan(args: argparse.Namespace) -> int:
    config = load_config()
    tickers = universe(config)
    target = getattr(args, "date", None)
    if not tickers:
        print("No universe configured; nothing to scan.")
        return 0
    print(f"=== Daily Market Scan ({len(tickers)} symbols)"
          + (f" @ {target}" if target else "") + " ===")
    if yf is None:
        print("  [WARN] yfinance not installed; skipping live quotes.")
        return 0
    print(f"  {'TICKER':8} {'LAST':>10} {'CHG%':>8}")
    for tk in tickers:
        try:
            hist = yf.Ticker(tk).history(period="2d")
            if hist is None or hist.empty or len(hist) < 2:
                print(f"  {tk:8} {'n/a':>10} {'n/a':>8}")
                continue
            last = float(hist["Close"].iloc[-1])
            prev = float(hist["Close"].iloc[-2])
            chg = (last / prev - 1.0) * 100.0 if prev else 0.0
            print(f"  {tk:8} {last:>10.2f} {chg:>+8.2f}")
        except Exception as exc:
            print(f"  {tk:8} {'n/a':>10} {'n/a':>8}   [WARN] {exc}")
    return 0


def _not_implemented(name: str) -> int:
    print(f"[NOT IMPLEMENTED] `{name}` requires portfolio state / execution and is "
          f"not yet wired to the engine. Exiting cleanly (no-op).")
    return 0


def cmd_rebalance(args: argparse.Namespace) -> int:
    return _not_implemented("rebalance")


def cmd_backtest(args: argparse.Namespace) -> int:
    return _not_implemented("backtest")


def cmd_monte_carlo(args: argparse.Namespace) -> int:
    return _not_implemented("monte-carlo")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="ai_hedge_fund",
                                description="AI Hedge Fund research/scan CLI")
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("status", help="System health check")
    sub.add_parser("snapshot", help="Current portfolio state")
    sub.add_parser("scan", help="Daily portfolio scan with signals")
    sub.add_parser("rebalance", help="Full sleeve rebalancing")
    sub.add_parser("backtest", help="Historical walk-forward backtest")
    sub.add_parser("monte-carlo", help="Block bootstrap stress test")
    for name in ("scan", "backtest"):
        sub.choices[name].add_argument(
            "--date", help="target date (YYYY-MM-DD)", default=None)
    return p


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    handlers = {
        "status": cmd_status,
        "snapshot": cmd_snapshot,
        "scan": cmd_scan,
        "rebalance": cmd_rebalance,
        "backtest": cmd_backtest,
        "monte-carlo": cmd_monte_carlo,
    }
    return handlers[args.command](args)


# Alias used by ai_hedge_fund/__main__.py (`from ai_hedge_fund import run_cli`)
run_cli = main


if __name__ == "__main__":
    sys.exit(main())
