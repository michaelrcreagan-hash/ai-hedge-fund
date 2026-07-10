"""
Bottleneck Capital — Main Orchestrator
Coordinates: 4-Sleeve Portfolio + IMAW v2.0 + Risk Manager + Paper Trader
Single entry point for the entire agentic hedge fund
"""
import os
import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from pathlib import Path

from src.config import (
    SleeveParams, PORTFOLIO_TARGETS, EXPERT_BRAINS,
    LAYER_CAKE_TICKERS, SIGNALS_CONFIG, TECE_CONFIG
)
from src.data_layer import MarketDataFetcher
from src.sleeve_engine import FourSleevePortfolio, RegimeDetector
from src.imaw_engine import IMAWorkflow
from src.risk_manager import RiskManager
from src.paper_trader import PaperTrader


class BottleneckFundOrchestrator:
    """
    Central orchestrator — the 'CEO Agent' that coordinates all departments
    
    Architecture (from Bottleneck Capital PDF):
    - Research Department (IMAW Phase 1-3)
    - Quant Department (IMAW Phase 4-5)
    - Portfolio Management (4-Sleeve Engine)
    - Risk Management (Kill Switches + Drawdown)
    - Execution (Paper Trader)
    - CIO Review (Final signal approval)
    """
    
    def __init__(self, 
                 initial_capital: float = 50000,
                 alpaca_key: str = None,
                 alpaca_secret: str = None):
        
        self.capital = initial_capital
        self.params = SleeveParams()
        
        self.data = MarketDataFetcher(cache_dir="cache", cache_ttl_hours=1)
        self.portfolio = FourSleevePortfolio(self.params)
        self.imaw = IMAWorkflow()
        self.risk = RiskManager(initial_capital)
        self.trader = PaperTrader(alpaca_key, alpaca_secret, initial_capital=initial_capital)
        self.regime_detector = RegimeDetector()
        
        self.current_regime = "MIXED"
        self.universe_data = {}
        self.latest_signals = []
        self.last_update = None
        
        self.equity_curve = [(datetime.now().isoformat(), initial_capital)]
        self.daily_log = []
    
    def refresh_data(self, tickers: Optional[List[str]] = None) -> Dict[str, any]:
        if tickers is None:
            tickers = []
            for layer in LAYER_CAKE_TICKERS.values():
                tickers.extend(layer)
            tickers.extend(["SPY", "QQQ", "SMH", "GLD", "TLT", "^VIX"])
            tickers = list(set(tickers))
        
        print(f"[Orchestrator] Fetching data for {len(tickers)} tickers...")
        self.universe_data = self.data.fetch_batch(tickers, "1d", "6mo")
        self.last_update = datetime.now().isoformat()
        
        return {"tickers_fetched": len(self.universe_data), "timestamp": self.last_update}
    
    def run_regime_detection(self) -> Dict:
        smh = self.universe_data.get("SMH")
        vix_df = self.universe_data.get("^VIX")
        
        smh_price = smh['close'].iloc[-1] if smh is not None and len(smh) > 0 else 0
        smh_200dma = smh['close'].rolling(200).mean().iloc[-1] if smh is not None and len(smh) > 200 else smh_price
        vix = vix_df['close'].iloc[-1] if vix_df is not None and len(vix_df) > 0 else 25
        
        self.current_regime = self.regime_detector.detect(
            vix=vix, smh_price=smh_price, smh_200dma=smh_200dma
        )
        
        tece_score, tece_regime = self.regime_detector.compute_tece_score()
        
        return {
            "regime": self.current_regime,
            "vix": round(vix, 2),
            "smh_price": round(smh_price, 2),
            "smh_200dma": round(smh_200dma, 2),
            "smh_above_200dma": smh_price > smh_200dma,
            "tece_score": tece_score,
            "tece_regime": tece_regime,
        }
    
    def run_imaw_pipeline(self) -> List[Dict]:
        if not self.universe_data:
            return []
        
        print(f"[Orchestrator] Running IMAW pipeline in regime: {self.current_regime}")
        signals = self.imaw.run_universe(self.universe_data, self.current_regime)
        
        self.latest_signals = [s for s in signals 
                              if s["phase7_signal"]["signal_type"] in ["CONFIRMED", "PRELIMINARY"]]
        
        return self.latest_signals[:10]
    
    def run_risk_check(self) -> Dict:
        smh = self.universe_data.get("SMH")
        vix_df = self.universe_data.get("^VIX")
        
        smh_price = smh['close'].iloc[-1] if smh is not None else 0
        smh_200dma = smh['close'].rolling(200).mean().iloc[-1] if smh is not None and len(smh) > 200 else smh_price
        vix = vix_df['close'].iloc[-1] if vix_df is not None else None
        
        current_value = self.trader.get_portfolio_value({})
        
        result = self.risk.pre_trade_check(
            vix=vix, smh_price=smh_price, smh_200dma=smh_200dma, portfolio_dd_pct=0,
        )
        
        return result
    
    def generate_trades(self, top_signals: List[Dict]) -> List[Dict]:
        trades = []
        
        for signal in top_signals:
            ticker = signal["ticker"]
            df = self.universe_data.get(ticker)
            if df is None or df.empty:
                continue
            
            price = df['close'].iloc[-1]
            atr = df['atr'].iloc[-1] if 'atr' in df.columns else price * 0.02
            stop = price - 2 * atr
            target = price + 3 * atr
            
            vix_df = self.universe_data.get("^VIX")
            vix = vix_df['close'].iloc[-1] if vix_df is not None else None
            
            sizing = self.risk.size_position(price, stop, vix)
            
            if sizing["valid"] and sizing["shares"] > 0:
                trades.append({
                    "ticker": ticker, "action": "BUY", "shares": sizing["shares"],
                    "entry": round(price, 2), "stop": round(stop, 2), "target": round(target, 2),
                    "risk_reward": round((target - price) / (price - stop), 2) if (price - stop) > 0 else 0,
                    "size_usd": sizing["size_usd"], "risk_pct": sizing["risk_pct"],
                    "signal_score": signal["phase7_signal"]["total_score"],
                    "sleeve": "innovation",
                })
        
        return trades
    
    def execute_trades(self, trades: List[Dict]) -> List[Dict]:
        results = []
        
        for trade in trades[:5]:
            result = self.trader.buy(
                ticker=trade["ticker"], shares=trade["shares"], sleeve=trade["sleeve"],
                signal_type="IMAW", stop_price=trade["stop"], target_price=trade["target"],
                current_price=trade["entry"],
            )
            results.append(result)
        
        return results
    
    def run_full_cycle(self) -> Dict:
        cycle_log = {"timestamp": datetime.now().isoformat()}
        
        data_status = self.refresh_data()
        cycle_log["data"] = data_status
        
        regime = self.run_regime_detection()
        cycle_log["regime"] = regime
        self.current_regime = regime["regime"]
        self.portfolio.current_regime = self.current_regime
        
        signals = self.run_imaw_pipeline()
        cycle_log["signals"] = {
            "total_screened": len(signals),
            "confirmed": len([s for s in signals if s["phase7_signal"]["signal_type"] == "CONFIRMED"]),
            "preliminary": len([s for s in signals if s["phase7_signal"]["signal_type"] == "PRELIMINARY"]),
            "top_tickers": [s["ticker"] for s in signals[:5]],
        }
        
        risk_check = self.run_risk_check()
        cycle_log["risk"] = risk_check
        
        executed = []
        if risk_check["status"] in ["GO", "GO_HALVED"]:
            confirmed = [s for s in signals if s["phase7_signal"]["signal_type"] == "CONFIRMED"][:5]
            if confirmed:
                trades = self.generate_trades(confirmed)
                cycle_log["trades_generated"] = len(trades)
                if trades:
                    executed = self.execute_trades(trades)
                    cycle_log["trades_executed"] = len(executed)
        else:
            cycle_log["trades_generated"] = 0
            cycle_log["trades_executed"] = 0
            cycle_log["skip_reason"] = risk_check["reason"]
        
        prices = {t: df['close'].iloc[-1] for t, df in self.universe_data.items()}
        self.trader.update_positions(prices)
        portfolio = self.trader.get_dashboard(prices)
        cycle_log["portfolio"] = portfolio
        
        self.equity_curve.append((datetime.now().isoformat(), portfolio["total_value"]))
        self.daily_log.append(cycle_log)
        
        return cycle_log
    
    def get_full_dashboard(self) -> Dict:
        prices = {t: df['close'].iloc[-1] for t, df in self.universe_data.items()}
        
        portfolio = self.trader.get_dashboard(prices)
        
        regime = {
            "current": self.current_regime,
            "weights": self.portfolio.compute_target_allocation(),
        }
        
        risk = self.risk.get_dashboard()
        
        top_signals = []
        for s in self.latest_signals[:5]:
            top_signals.append({
                "ticker": s["ticker"],
                "score": s["phase7_signal"]["total_score"],
                "type": s["phase7_signal"]["signal_type"],
                "tech_score": s["phase4_technical"]["combined_tech_score"],
                "tier": s["phase5_four_factor"]["tier"],
            })
        
        experts = []
        for key, brain in EXPERT_BRAINS.items():
            experts.append({
                "name": brain["name"],
                "focus": brain["focus"],
                "thesis_summary": brain["thesis"],
            })
        
        live_signals = []
        for key, sig in SIGNALS_CONFIG.items():
            live_signals.append({
                "name": sig["name"],
                "trigger": sig["trigger"],
                "weight": sig["weight"],
            })
        
        return {
            "fund_name": "Bottleneck Capital — Agentic Hedge Fund",
            "timestamp": datetime.now().isoformat(),
            "regime": regime,
            "portfolio": portfolio,
            "risk": risk,
            "top_signals": top_signals,
            "expert_brains": experts,
            "live_signals": live_signals,
            "equity_curve": self.equity_curve[-30:],
            "targets": {
                "initial_capital": PORTFOLIO_TARGETS["initial_capital"],
                "current_value": portfolio["total_value"],
                "phase1_target": PORTFOLIO_TARGETS["phase1_target_value"],
                "phase1_date": PORTFOLIO_TARGETS["phase1_target_date"],
                "phase2_target": PORTFOLIO_TARGETS["phase2_target_value"],
                "phase2_date": PORTFOLIO_TARGETS["phase2_target_date"],
            },
        }
