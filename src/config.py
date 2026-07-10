---
name: config
description: >
  Bottleneck Capital Fund Configuration
  Consolidated from all research documents and optimization reports.
  All parameters are the optimized values from the grid search.
---

# ═════════════════════════════════════════════════════════════════════════════
# 4-SLEEVE PORTFOLIO — OPTIMIZED PARAMETERS (from OPTIMIZATION_REPORT.md)
# ═════════════════════════════════════════════════════════════════════════════

import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import List, Dict, Tuple
from datetime import datetime

@dataclass
class SleeveParams:
    """Optimized sleeve parameters from grid search (IS/OOS validated)"""
    # S1 Macro: trend gate OFF, inverse-vol weighting
    macro_trend_gate: bool = False  # Gate whipsawed; OFF is better OOS
    macro_selection: str = "inverse-vol"  # Equal-weight and top-4 unstable
    
    # S2 Income: "both" variant — halve TLT below 200DMA + GLD when corr>0
    income_variant: str = "both"  # "static", "regime", or "both"
    
    # S3 Innovation: 63d momentum, top 4, vol target 0.35
    innovation_top_n: int = 4
    momentum_window: int = 63  # 126d too slow; 63d best OOS
    innovation_vol_target: float = 0.35  # Daniel-Moskowitz crash guard
    
    # S4 Options: delta 0.22 diagonal
    options_short_delta: float = 0.22
    options_leg: str = "sell"  # PMCC diagonal

# ═════════════════════════════════════════════════════════════════════════════
# REGIME MATRIX (from SLEEVE_BACKTEST_REPORT.md)
# RISK-ON → MIXED → CAUTION → RISK-OFF
# ═════════════════════════════════════════════════════════════════════════════

REGIME_WEIGHTS = {
    "RISK_ON":   {"macro": 0.40, "income": 0.15, "innovation": 0.35, "options": 0.10, "cash": 0.00},
    "MIXED":     {"macro": 0.30, "income": 0.25, "innovation": 0.25, "options": 0.10, "cash": 0.10},
    "CAUTION":   {"macro": 0.15, "income": 0.40, "innovation": 0.15, "options": 0.05, "cash": 0.25},
    "RISK_OFF":  {"macro": 0.05, "income": 0.50, "innovation": 0.00, "options": 0.00, "cash": 0.45},
}

REGIME_THRESHOLDS = {
    "risk_on_vix_max": 18,
    "risk_off_vix_min": 30,
    "trend_ma_period": 200,
    "mixed_buffer": 5,
}

# ═════════════════════════════════════════════════════════════════════════════
# AI LAYER CAKE — TICKER UNIVERSE (from RESEARCH.md + OMEGA DASHBOARD)
# ═════════════════════════════════════════════════════════════════════════════

LAYER_CAKE_TICKERS = {
    "L1_Compute":    ["NVDA", "AMD", "AVGO", "TSM", "MU"],
    "L2_Fab":        ["AMAT", "LRCX", "KLAC", "ASML", "ONTO"],
    "L3_Net":        ["MRVL", "CRDO", "ANET", "ALAB"],
    "L4_Infra":      ["VRT", "ETN", "PWR", "CEG", "VST"],
    "L5_SW":         ["MSFT", "GOOGL", "META", "ORCL", "SNOW", "PLTR"],
    "L6_App":        ["UBER", "DUOL", "APP"],
}

# ═════════════════════════════════════════════════════════════════════════════
# IMAW v2.0 CONFIGURATION (from IMAW documents)
# ═════════════════════════════════════════════════════════════════════════════

IMAW_CONFIG = {
    "weights": {
        "phase1_regime_fit": 0.20,
        "phase2_theme_opportunity": 0.25,
        "phase3_flow_momentum": 0.10,
        "phase4_technical": 0.20,
        "phase5_expert_synthesis": 0.15,
        "phase6_risk_reward": 0.10,
    },
    "technical": {
        "ema_fast": 8,
        "ema_mid": 21,
        "ema_slow": 50,
        "ema_long": 200,
        "rsi_period": 14,
        "rsi_ob": 70,
        "rsi_os": 30,
        "adx_period": 14,
        "adx_threshold": 20,
        "atr_period": 14,
        "supertrend_period": 10,
        "supertrend_mult": 3.0,
        "stoch_k": 14,
        "stoch_d": 3,
        "roc_period": 10,
        "vol_expansion_ratio": 1.2,
        "pullback_atr_mult": 1.5,
        "invalidation_atr_mult": 2.0,
        "obv_ma_period": 20,
        "rel_vol_period": 20,
        "bb_length": 20,
        "bb_mult": 2.0,
    },
    "weekly_gate": {
        "pass_threshold": 4.0,
        "adx_strong_bonus": 1.5,
        "dmi_bullish_bonus": 1.0,
        "rob_booker_bonus": 1.5,
        "supertrend_bonus": 1.2,
        "vol_expansion_bonus": 0.8,
        "stoch_bonus": 0.8,
        "roc_bonus": 0.7,
    },
    "daily_gate": {
        "ema_stack_bonus": 1.8,
        "adx_above_20_bonus": 1.2,
        "rsi_above_50_bonus": 0.8,
        "supertrend_bonus": 1.3,
        "obv_bonus": 1.1,
        "breakout_rel_vol_bonus": 1.6,
        "pullback_atr_bonus": 2.2,
    },
    "scoring": {
        "min_confirmed_score": 8.0,
        "preliminary_score_threshold": 5.0,
    },
}

# ═════════════════════════════════════════════════════════════════════════════
# RISK MANAGEMENT — KILL SWITCHES & DRAWDOWN CONTROLS
# ═════════════════════════════════════════════════════════════════════════════

RISK_CONFIG = {
    "kill_vix_level": 30,
    "kill_smh_below_200dma": True,
    "kill_10y_above_5_and_ism_below_48": True,
    "kill_realized_vol_20d_above_40": True,
    "kill_3_tier1_miss_eps": True,
    "kill_portfolio_dd_15pct": True,
    "de-risk_10pct_dd": "halve_new_risk",
    "de-risk_15pct_dd": "pause_new_entries",
    "de-risk_20pct_dd": "flat_except_hedges",
    "max_single_name_pct": 0.15,
    "max_total_bottleneck_pct": 0.60,
    "max_options_loss_per_trade": 500,
    "risk_per_trade_pct": 0.01,
    "hedge_budget_pct": 0.02,
    "standing_hedge": "smh_put_debit_spread",
    "vix_hedge_trigger": 25,
    "iv_rank": {
        "ivr_lt_30": "bull_call_debit_spread",
        "ivr_30_50": "wider_debit_spread",
        "ivr_50_70": "bull_put_credit_spread",
        "ivr_gt_70": "iron_condor_or_csp",
        "binary_event": "half_size_only",
    },
}

# ═════════════════════════════════════════════════════════════════════════════
# TECE REGIME SCORECARD
# ═════════════════════════════════════════════════════════════════════════════

TECE_CONFIG = {
    "factors": {
        "T": {"name": "Tech Earnings Revisions", "weight": 1.0},
        "E": {"name": "Employment/Macro", "weight": 1.0},
        "C": {"name": "Credit Conditions", "weight": 1.0},
        "E2": {"name": "Equity Risk Appetite", "weight": 1.0},
    },
    "thresholds": {
        "RISK_ON": (8, 12, "60% equity / 50% margin"),
        "MIXED": (5, 7, "45% equity / 30% margin"),
        "CAUTION": (3, 4, "25% equity / 10% margin"),
        "RISK_OFF": (0, 2, "Flat / hedges only"),
    },
}

# ═════════════════════════════════════════════════════════════════════════════
# 7 LIVE SIGNALS (from OMEGA Dashboard)
# ═════════════════════════════════════════════════════════════════════════════

SIGNALS_CONFIG = {
    "signal1_upward_revision_velocity": {
        "name": "Upward Earnings Revision Velocity",
        "trigger": ">+5 names revised up in 4 weeks = BUY",
        "weight": 0.20,
    },
    "signal2_rvol_theme_outperformers": {
        "name": "RVOL Theme Outperformers",
        "trigger": "RVOL >1.5x avg = ENTER THEME",
        "weight": 0.15,
    },
    "signal3_technical_momentum": {
        "name": "Technical Momentum Screen",
        "trigger": "RSI 50-65 + above 20MA = CONFIRM",
        "weight": 0.15,
    },
    "signal4_fundamental_score": {
        "name": "Fundamental Score Screen",
        "trigger": "Four-Factor Score >= 20/25 = Tier-1",
        "weight": 0.15,
    },
    "signal5_healthy_financials": {
        "name": "Healthy Financials Screen",
        "trigger": "FCF+, D/E<1, EPS up = QUALITY",
        "weight": 0.10,
    },
    "signal6_emerging_theme_radar": {
        "name": "Emerging Theme Radar",
        "trigger": ">=3 signals on new theme = WATCH",
        "weight": 0.10,
    },
    "signal7_benchmark_peer_outperformers": {
        "name": "Benchmark/Peer Outperformers",
        "trigger": "RS line new 52w high = PRIORITY",
        "weight": 0.15,
    },
}

# ═════════════════════════════════════════════════════════════════════════════
# FOUR-FACTOR MODEL
# ═════════════════════════════════════════════════════════════════════════════

FOUR_FACTOR_WEIGHTS = {
    "earnings_revision_momentum": 0.40,
    "relative_strength": 0.25,
    "scarcity_moat_durability": 0.20,
    "technicals": 0.15,
}

TIER_THRESHOLDS = {
    "TIER_1": 20,
    "TIER_2": 16,
    "TIER_3": 12,
    "WATCH": 0,
}

# ═════════════════════════════════════════════════════════════════════════════
# BOTTLENECK PHASE ROTATION
# ═════════════════════════════════════════════════════════════════════════════

BOTTLENECK_PHASES = {
    "2022-2023": ["memory", "gpu"],
    "2024": ["optics", "memory", "power"],
    "2025-2026": ["power", "cooling", "optics"],
    "2027-2028": ["physical_ai", "robotics", "agentic"],
}

# ═════════════════════════════════════════════════════════════════════════════
# EXPERT KNOWLEDGE BRAINS
# ═════════════════════════════════════════════════════════════════════════════

EXPERT_BRAINS = {
    "leopold": {
        "name": "Leopold Aschenbrenner",
        "focus": "AGI infrastructure, power/compute arbitrage",
        "thesis": "Long power/compute infra, selective shorts on overvalued hardware",
        "key_assets": ["VRT", "VST", "CEG", "MU", "NVDA"],
        "ramp_date": "2024-06-01",
    },
    "visser": {
        "name": "Jordi Visser",
        "focus": "AI Macro Nexus, liquidity, Bitcoin",
        "thesis": "AI disrupts macro; BTC is purest AI trade; rotate to infra/value",
        "key_assets": ["BTC", "MSTR", "VRT", "MU"],
    },
    "wolff": {
        "name": "Peter Wolff",
        "focus": "Growth-at-reasonable-valuation, quality compounders",
        "thesis": "Buy dips in quality, trim strength, add precious metals defense",
        "key_assets": ["MSFT", "GOOGL", "META", "GLD"],
    },
    "jenson": {
        "name": "Jenson/Jensen",
        "focus": "Semiconductor ecosystem, supply chain",
        "thesis": "Hardware demand strong; watch capex ROI and supply ramps",
        "key_assets": ["NVDA", "AMD", "TSM", "AVGO", "MRVL"],
    },
}

# ═════════════════════════════════════════════════════════════════════════════
# ALPACA CONFIGURATION
# ═════════════════════════════════════════════════════════════════════════════

ALPACA_CONFIG = {
    "paper": True,
    "base_url": "https://paper-api.alpaca.markets",
    "data_url": "https://data.alpaca.markets",
    "api_version": "v2",
}

# ═════════════════════════════════════════════════════════════════════════════
# PORTFOLIO TARGETS
# ═════════════════════════════════════════════════════════════════════════════

PORTFOLIO_TARGETS = {
    "initial_capital": 50000,
    "monthly_contribution": 2000,
    "phase1_target_date": "2029-12-31",
    "phase1_target_value": 2000000,
    "phase2_target_date": "2055-12-31",
    "phase2_target_value": 10000000,
    "conservative_cagr": 0.35,
    "base_case_cagr": 0.55,
    "bull_case_cagr": 0.75,
    "supercycle_cagr": 0.92,
}
