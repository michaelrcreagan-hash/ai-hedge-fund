"""Smoke tests: every CLI subcommand must exit 0 (so scheduled CI stays green)."""
from ai_hedge_fund.cli import main


def test_status_exits_zero():
    assert main(["status"]) == 0


def test_snapshot_exits_zero():
    assert main(["snapshot"]) == 0


def test_scan_exits_zero():
    assert main(["scan"]) == 0


def test_rebalance_exits_zero():
    assert main(["rebalance"]) == 0


def test_backtest_exits_zero():
    assert main(["backtest"]) == 0


def test_monte_carlo_exits_zero():
    assert main(["monte-carlo"]) == 0
