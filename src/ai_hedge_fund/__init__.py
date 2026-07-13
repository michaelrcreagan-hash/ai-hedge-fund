"""AI Hedge Fund System - multi-sleeve quantitative research CLI.

Read-only research/scan toolkit. No live trading is performed by this package.
See ``ai_hedge_fund.cli`` for command-line entry points.
"""

__version__ = "1.0.0"

from ai_hedge_fund.cli import run_cli  # noqa: E402,F401  (re-exported CLI entry)
