"""Configuration loading for the AI Hedge Fund research toolkit."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

_DEFAULT_PATH = Path(__file__).resolve().parents[2] / "config.yaml"

# Regime keys live at the top level of config.yaml.
REGIME_KEYS = ("risk_on", "mixed", "caution", "risk_off")


def load_config(path: str | Path | None = None) -> dict[str, Any]:
    """Load config.yaml. Falls back to the repo-root config.yaml."""
    cfg_path = Path(path) if path else _DEFAULT_PATH
    with open(cfg_path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def sleeve_allocations(regime: str = "risk_on", config: dict[str, Any] | None = None) -> dict[str, float]:
    """Return the sleeve allocation dict for a given regime."""
    config = config or load_config()
    return dict(config.get(regime, config.get("risk_on", {})))
