"""
Risk Management: Kill Switches, Drawdown Controls, Position Sizing
Central nervous system of the fund — non-overridable hard stops
"""
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

from src.config import RISK_CONFIG


class KillSwitchEngine:
    """Non-overridable hard kill switches"""
    
    def __init__(self):
        self.config = RISK_CONFIG
        self.triggered = []
        self.last_check = None
    
    def check_all(self, vix: Optional[float], smh_price: float, 
                  smh_200dma: float, yield_10y: float = 0,
                  ism: float = 50, realized_vol_20d: float = 0,
                  tier1_eps_misses: int = 0, portfolio_dd_pct: float = 0) -> List[str]:
        triggered = []
        
        if vix and vix > self.config["kill_vix_level"]:
            triggered.append(f"VIX={vix:.1f} > {self.config['kill_vix_level']}")
        
        if smh_price < smh_200dma:
            triggered.append(f"SMH={smh_price:.2f} < 200DMA={smh_200dma:.2f}")
        
        if yield_10y > 5.0 and ism < 48:
            triggered.append(f"10Y={yield_10y:.2f}% > 5% AND ISM={ism:.1f} < 48")
        
        if realized_vol_20d > 0.40:
            triggered.append(f"RealizedVol={realized_vol_20d:.1%} > 40%")
        
        if tier1_eps_misses >= 3:
            triggered.append(f"Tier1 EPS misses={tier1_eps_misses}")
        
        if portfolio_dd_pct > 0.15:
            triggered.append(f"Portfolio DD={portfolio_dd_pct:.1%} > 15%")
        
        self.triggered = triggered
        self.last_check = datetime.now()
        return triggered
    
    @property
    def is_killed(self) -> bool:
        return len(self.triggered) > 0
    
    @property
    def action(self) -> str:
        if self.is_killed:
            return "FLAT_EXCEPT_HEDGES"
        return "NORMAL"


class DrawdownController:
    """Staged de-risking based on portfolio drawdown"""
    
    def __init__(self):
        self.peak_value = 0
        self.current_dd = 0.0
        self.status = "NORMAL"
    
    def update(self, portfolio_value: float) -> str:
        if portfolio_value > self.peak_value:
            self.peak_value = portfolio_value
        
        if self.peak_value > 0:
            self.current_dd = (self.peak_value - portfolio_value) / self.peak_value
        
        if self.current_dd > 0.20:
            self.status = "FLAT"
            return "flat_except_hedges"
        elif self.current_dd > 0.15:
            self.status = "PAUSE"
            return "pause_new_entries"
        elif self.current_dd > 0.10:
            self.status = "HALVE"
            return "halve_new_risk"
        else:
            self.status = "NORMAL"
            return "normal"
    
    def get_status(self) -> Dict:
        return {
            "peak_value": self.peak_value,
            "current_dd_pct": round(self.current_dd * 100, 2),
            "status": self.status,
        }


class PositionSizer:
    """Kelly-inspired position sizing with volatility scaling"""
    
    def __init__(self, config: dict = None):
        self.config = config or RISK_CONFIG
    
    def compute_size(self, portfolio_value: float, entry_price: float,
                    stop_price: float, conviction: float = 0.5,
                    vix: Optional[float] = None) -> Dict:
        risk_amount = portfolio_value * self.config["risk_per_trade_pct"]
        stop_dist = entry_price - stop_price
        
        if stop_dist <= 0:
            return {"shares": 0, "size_usd": 0, "risk": 0, "valid": False}
        
        shares = int(risk_amount / stop_dist)
        size_usd = shares * entry_price
        
        max_size = portfolio_value * self.config["max_single_name_pct"]
        if size_usd > max_size:
            shares = int(max_size / entry_price)
            size_usd = shares * entry_price
        
        if vix and vix > 25:
            vix_scalar = max(0.3, 1 - (vix - 25) / 50)
            shares = int(shares * vix_scalar)
            size_usd = shares * entry_price
        
        return {
            "shares": shares,
            "size_usd": round(size_usd, 2),
            "risk": round(shares * stop_dist, 2),
            "risk_pct": round((shares * stop_dist) / portfolio_value * 100, 2),
            "stop_dist": round(stop_dist, 2),
            "stop_pct": round(stop_dist / entry_price * 100, 2),
            "valid": shares > 0,
        }
    
    def options_size(self, portfolio_value: float, max_loss: float = None) -> Dict:
        if max_loss is None:
            max_loss = self.config["max_options_loss_per_trade"]
        
        max_portfolio_risk = portfolio_value * self.config["risk_per_trade_pct"]
        actual_max_loss = min(max_loss, max_portfolio_risk)
        
        return {
            "max_loss": round(actual_max_loss, 2),
            "max_loss_pct": round(actual_max_loss / portfolio_value * 100, 2),
            "sizing_rule": "Max loss <= $500 (or 1% portfolio, whichever is smaller)",
        }


class HedgeManager:
    """Macro hedge overlay: SMH/QQQ put spreads, VIX calls"""
    
    def __init__(self, config: dict = None):
        self.config = config or RISK_CONFIG
    
    def recommend_hedge(self, regime: str, portfolio_value: float,
                       vix: Optional[float] = None) -> Dict:
        budget = portfolio_value * self.config["hedge_budget_pct"]
        
        hedge = {
            "budget": round(budget, 2),
            "budget_pct": self.config["hedge_budget_pct"] * 100,
            "structures": [],
        }
        
        if regime == "RISK_OFF" or (vix and vix > 25):
            hedge["structures"] = [
                {"type": "SMH_put_debit_spread", "description": "Buy SMH put ATM, sell put 5% OTM", "allocation": budget * 0.5},
                {"type": "VIX_call", "description": "Buy VIX calls for convexity", "allocation": budget * 0.3},
                {"type": "TLT_long", "description": "Long TLT as flight-to-safety", "allocation": budget * 0.2},
            ]
        elif regime == "MIXED":
            hedge["structures"] = [
                {"type": "QQQ_put_spread", "description": "Defined-risk put spread on QQQ", "allocation": budget * 0.4},
                {"type": "GLD_tilt", "description": "Increase GLD allocation", "allocation": budget * 0.3},
            ]
        else:
            hedge["structures"] = [
                {"type": "standing_insurance", "description": "Small VIX call or SMH put spread", "allocation": budget * 0.2}
            ]
        
        return hedge


class OptionsDecisionTree:
    """IV-Rank based options strategy selection"""
    
    def __init__(self):
        self.iv_tree = RISK_CONFIG["iv_rank"]
    
    def select_strategy(self, iv_rank: float, is_binary_event: bool = False,
                       direction: str = "bullish") -> Dict:
        if is_binary_event:
            return {
                "strategy": self.iv_tree["binary_event"],
                "description": "Half-size position only for binary events",
                "max_loss": 250,
                "rationale": "Earnings/FDA/macro event → size to $250 max loss",
            }
        
        if iv_rank < 30:
            strategy = self.iv_tree["ivr_lt_30"]
            rationale = "Low IV → pay for directional exposure"
            max_loss = "debit_paid"
        elif iv_rank < 50:
            strategy = self.iv_tree["ivr_30_50"]
            rationale = "Moderate IV → balance cost vs width"
            max_loss = "debit_paid"
        elif iv_rank < 70:
            strategy = self.iv_tree["ivr_50_70"]
            rationale = "Elevated IV → sell premium, collect credit"
            max_loss = "width_minus_credit"
        else:
            strategy = self.iv_tree["ivr_gt_70"]
            rationale = "High IV → premium harvest, neutral to bullish"
            max_loss = "defined_risk"
        
        return {
            "strategy": strategy,
            "description": rationale,
            "max_loss_rule": max_loss,
            "iv_rank": iv_rank,
        }


class RiskManager:
    """Centralized risk management — all departments feed into this"""
    
    def __init__(self, portfolio_value: float = 50000):
        self.kill_switch = KillSwitchEngine()
        self.drawdown = DrawdownController()
        self.sizer = PositionSizer()
        self.hedge = HedgeManager()
        self.options_tree = OptionsDecisionTree()
        self.portfolio_value = portfolio_value
        self.risk_log = []
    
    def pre_trade_check(self, **market_data) -> Dict:
        kills = self.kill_switch.check_all(**market_data)
        dd_action = self.drawdown.update(self.portfolio_value)
        dd_status = self.drawdown.get_status()
        
        if self.kill_switch.is_killed:
            status = "NO_GO"
            reason = f"KILL SWITCHES ACTIVE: {'; '.join(kills)}"
        elif dd_action == "flat_except_hedges":
            status = "NO_GO"
            reason = "Portfolio drawdown > 20% — flat except hedges"
        elif dd_action == "pause_new_entries":
            status = "NO_GO_NEW"
            reason = "Portfolio drawdown > 15% — no new entries"
        elif dd_action == "halve_new_risk":
            status = "GO_HALVED"
            reason = "Portfolio drawdown > 10% — halve new risk"
        else:
            status = "GO"
            reason = "All clear"
        
        result = {
            "status": status,
            "reason": reason,
            "kill_switches": kills,
            "drawdown": dd_status,
            "timestamp": datetime.now().isoformat(),
        }
        
        self.risk_log.append(result)
        return result
    
    def size_position(self, entry_price: float, stop_price: float,
                     vix: Optional[float] = None) -> Dict:
        dd_status = self.drawdown.get_status()
        
        scalar = 1.0
        if dd_status["status"] == "HALVE":
            scalar = 0.5
        elif dd_status["status"] in ["PAUSE", "FLAT"]:
            scalar = 0.0
        
        size = self.sizer.compute_size(
            self.portfolio_value, entry_price, stop_price, vix=vix
        )
        
        size["shares"] = int(size["shares"] * scalar)
        size["size_usd"] = round(size["shares"] * entry_price, 2)
        size["scalar"] = scalar
        
        return size
    
    def get_dashboard(self) -> Dict:
        return {
            "kill_switches": {
                "active": self.kill_switch.is_killed,
                "triggered": self.kill_switch.triggered,
                "last_check": self.kill_switch.last_check,
            },
            "drawdown": self.drawdown.get_status(),
            "position_limits": {
                "max_single_name_pct": self.sizer.config["max_single_name_pct"] * 100,
                "max_bottleneck_pct": self.sizer.config["max_total_bottleneck_pct"] * 100,
                "risk_per_trade_pct": self.sizer.config["risk_per_trade_pct"] * 100,
                "max_options_loss": self.sizer.config["max_options_loss_per_trade"],
            },
            "hedge_budget_pct": self.hedge.config["hedge_budget_pct"] * 100,
            "portfolio_value": self.portfolio_value,
        }
