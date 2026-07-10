"""
IMAW v2.0 — Integrated Market Analysis Workflow
7-Phase Pipeline with Weekly Gate + Daily Gate System
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass

from src.config import IMAW_CONFIG, FOUR_FACTOR_WEIGHTS, TIER_THRESHOLDS, SIGNALS_CONFIG


class TechnicalGates:
    """Weekly Gate (higher timeframe) + Daily Gate (precise entry)"""
    
    def __init__(self, config: dict = None):
        self.cfg = config or IMAW_CONFIG
    
    def weekly_gate(self, df: pd.DataFrame) -> Tuple[float, bool, Dict]:
        if df.empty or len(df) < 30:
            return 0.0, False, {}
        
        row = df.iloc[-1]
        wg = self.cfg["weekly_gate"]
        score = 0.0
        details = {}
        
        adx = row.get('ADX', 0)
        plus_di = row.get('+DI', 50)
        minus_di = row.get('-DI', 50)
        
        if adx > self.cfg["technical"]["adx_threshold"]:
            score += wg["adx_strong_bonus"]
            details["adx_strong"] = True
        
        if plus_di > minus_di:
            score += wg["dmi_bullish_bonus"]
            details["dmi_bullish"] = True
        
        if row.get('rob_booker_bull', False):
            score += wg["rob_booker_bonus"]
            details["rob_booker_bull"] = True
        
        if row.get('SuperTrend_bull', False):
            score += wg["supertrend_bonus"]
            details["supertrend_bull"] = True
        
        if row.get('vol_expansion', False) and plus_di > minus_di:
            score += wg["vol_expansion_bonus"]
            details["vol_expansion_bull"] = True
        
        if row.get('stoch_bull_cross', False) or (row.get('%K', 50) > row.get('%D', 50)):
            score += wg["stoch_bonus"]
            details["stoch_bullish"] = True
        
        if row.get('ROC', 0) > 0:
            score += wg["roc_bonus"]
            details["roc_positive"] = True
        
        passed = score >= wg["pass_threshold"]
        return round(score, 2), passed, details
    
    def daily_gate(self, df: pd.DataFrame, weekly_score: float) -> Tuple[float, Dict]:
        if df.empty or len(df) < 30:
            return 0.0, {}
        
        row = df.iloc[-1]
        dg = self.cfg["daily_gate"]
        tech = self.cfg["technical"]
        score = weekly_score * 0.5
        details = {}
        
        adx = row.get('ADX', 0)
        if adx > 20:
            score += dg["adx_above_20_bonus"]
            details["adx_above_20"] = True
        
        ema8 = row.get('ema_8', np.nan)
        ema21 = row.get('ema_21', np.nan)
        ema50 = row.get('ema_50', np.nan) or row.get('ema_fast', np.nan)
        ema200 = row.get('sma_200', np.nan)
        
        if (not pd.isna(ema8) and not pd.isna(ema21) and 
            not pd.isna(ema50) and not pd.isna(ema200)):
            if ema8 > ema21 > ema50 > ema200:
                score += dg["ema_stack_bonus"]
                details["ema_stack_bullish"] = True
        
        if row.get('vol_expansion', False):
            score += dg["rsi_above_50_bonus"]
            details["vol_expansion"] = True
        
        rsi = row.get('rsi', 50)
        if rsi > 50:
            score += 0.8
            details["rsi_above_50"] = True
        
        if row.get('SuperTrend_bull', False):
            score += dg["supertrend_bonus"]
            details["supertrend_bull"] = True
        
        if row.get('OBV_trend', False):
            score += dg["obv_bonus"]
            details["obv_above_sma"] = True
        
        recent_high = df['high'].tail(20).max()
        is_breakout = row['close'] > recent_high * 0.995
        rel_vol = row.get('rel_vol', 1.0)
        
        if is_breakout and rel_vol > 1.25:
            score += dg["breakout_rel_vol_bonus"]
            details["breakout_with_rel_vol"] = True
            details["rel_vol_on_breakout"] = round(rel_vol, 2)
        elif rel_vol > 1.25:
            score += 0.8
            details["elevated_rel_vol"] = True
        
        atr = row.get('atr', np.nan)
        if not pd.isna(atr) and atr > 0:
            pullback_dist = (recent_high - row['close']) / atr
            if 0.5 < pullback_dist < 2.0:
                score += 0.7
                details["favorable_pullback"] = True
                details["pullback_atr"] = round(pullback_dist, 2)
        
        return round(score, 2), details
    
    def combined_score(self, df: pd.DataFrame) -> Dict:
        weekly_score, weekly_pass, weekly_details = self.weekly_gate(df)
        daily_score, daily_details = self.daily_gate(df, weekly_score)
        
        combined = min(weekly_score * 0.35 + daily_score * 0.65, 12.0)
        
        return {
            "weekly_gate_score": weekly_score,
            "weekly_gate_pass": weekly_pass,
            "weekly_details": weekly_details,
            "daily_gate_score": daily_score,
            "daily_details": daily_details,
            "combined_tech_score": round(combined, 2),
            "signal_strength": "CONFIRMED" if (weekly_pass and combined >= 8) else
                              "PRELIMINARY" if (combined >= 5) else "NONE"
        }


class OpportunityUniverse:
    """Generate focused opportunity list from AI Layer Cake + regime alignment"""
    
    def __init__(self):
        self.ai_infra_tickers = [
            "NVDA", "AMD", "AVGO", "TSM", "MU", "AMAT", "LRCX", "KLAC", "ASML", "ONTO",
            "MRVL", "CRDO", "ANET", "ALAB", "VRT", "ETN", "PWR", "CEG", "VST",
            "LITE", "COHR", "OKLO", "SMR", "IONQ", "MSTR", "HOOD"
        ]
    
    def screen(self, data: Dict[str, pd.DataFrame], regime: str) -> List[Dict]:
        candidates = []
        
        for ticker, df in data.items():
            if ticker not in self.ai_infra_tickers or len(df) < 50:
                continue
            
            row = df.iloc[-1]
            score = 0.0
            details = {}
            
            price = row['close']
            if price < 5:
                continue
            
            above_50dma = price > df['close'].rolling(50).mean().iloc[-1]
            if above_50dma:
                score += 1.5
                details["above_50dma"] = True
            
            ret_63d = price / df['close'].iloc[-64] - 1 if len(df) >= 64 else 0
            if ret_63d > 0:
                score += 1.0
                details["positive_momentum"] = True
            
            rsi = row.get('rsi', 50)
            if 40 < rsi < 75:
                score += 1.0
                details["healthy_rsi"] = True
            
            rel_vol = row.get('rel_vol', 1.0)
            if rel_vol > 1.0:
                score += 0.5
                details["volume_elevated"] = True
            
            if regime in ["RISK_ON", "MIXED"]:
                score += 1.0
                details["regime_aligned"] = True
            
            if score >= 3.0:
                candidates.append({
                    "ticker": ticker,
                    "score": round(score, 1),
                    "price": round(price, 2),
                    "rsi": round(rsi, 1) if not pd.isna(rsi) else None,
                    "rel_vol": round(rel_vol, 2) if not pd.isna(rel_vol) else None,
                    "return_63d": round(ret_63d * 100, 1),
                    "details": details,
                })
        
        candidates.sort(key=lambda x: x['score'], reverse=True)
        return candidates[:15]


class FourFactorModel:
    """Four-Factor Scoring: Earnings Revision (40%) + RS (25%) + Moat (20%) + Tech (15%)"""
    
    def __init__(self):
        self.weights = FOUR_FACTOR_WEIGHTS
    
    def score(self, ticker: str, df: pd.DataFrame, 
              revision_data: Optional[Dict] = None) -> Dict:
        if df.empty or len(df) < 50:
            return {"total": 0, "tier": "WATCH"}
        
        row = df.iloc[-1]
        scores = {}
        
        if revision_data and ticker in revision_data:
            rev_score = min(revision_data[ticker].get('velocity', 5), 10)
        else:
            ret_21d = row['close'] / df['close'].iloc[-22] - 1 if len(df) >= 22 else 0
            ret_63d = row['close'] / df['close'].iloc[-64] - 1 if len(df) >= 64 else 0
            rev_score = 5 + (ret_21d * 100) + (ret_63d * 50)
            rev_score = max(0, min(10, rev_score))
        scores['revision'] = round(rev_score, 1)
        
        ret_63d = row['close'] / df['close'].iloc[-64] - 1 if len(df) >= 64 else 0
        ret_252d = row['close'] / df['close'].iloc[-253] - 1 if len(df) >= 253 else 0
        rs_score = min(max(ret_63d * 100 + ret_252d * 50, 0), 6.25)
        scores['relative_strength'] = round(rs_score, 2)
        
        layer_scores = {
            "L1_Compute": 4.5, "L2_Fab": 4.5, "L3_Net": 4.0,
            "L4_Infra": 4.0, "L5_SW": 3.0, "L6_App": 2.5
        }
        moat_score = 3.0
        for layer, tickers in {
            "L1_Compute": ["NVDA", "AMD", "AVGO", "TSM", "MU"],
            "L2_Fab": ["AMAT", "LRCX", "KLAC", "ASML", "ONTO"],
            "L3_Net": ["MRVL", "CRDO", "ANET", "ALAB"],
            "L4_Infra": ["VRT", "ETN", "PWR", "CEG", "VST"],
            "L5_SW": ["MSFT", "GOOGL", "META", "ORCL", "SNOW", "PLTR"],
            "L6_App": ["UBER", "DUOL", "APP"],
        }.items():
            if ticker in tickers:
                moat_score = layer_scores[layer]
                break
        scores['moat'] = round(moat_score, 1)
        
        tech_score = 0
        if row.get('ema_8', 0) > row.get('ema_21', 0): tech_score += 0.5
        if row.get('rsi', 50) > 50: tech_score += 0.5
        if row.get('macd_bullish', False): tech_score += 0.5
        if row.get('rel_vol', 1) > 1.2: tech_score += 0.5
        if row.get('above_200sma', False): tech_score += 0.5
        tech_score = min(tech_score, 3.75)
        scores['technicals'] = round(tech_score, 2)
        
        total = (scores['revision'] * self.weights['earnings_revision_momentum'] +
                 scores['relative_strength'] * 4 +
                 scores['moat'] * self.weights['scarcity_moat_durability'] * 5 +
                 scores['technicals'] * 4)
        
        total = min(total, 25)
        
        if total >= TIER_THRESHOLDS['TIER_1']:
            tier = "TIER_1"
        elif total >= TIER_THRESHOLDS['TIER_2']:
            tier = "TIER_2"
        elif total >= TIER_THRESHOLDS['TIER_3']:
            tier = "TIER_3"
        else:
            tier = "WATCH"
        
        return {
            "ticker": ticker,
            "total_score": round(total, 1),
            "tier": tier,
            "factor_scores": scores,
        }


class IMAWorkflow:
    """Complete 7-Phase IMAW Pipeline"""
    
    def __init__(self):
        self.technical_gates = TechnicalGates()
        self.opportunity = OpportunityUniverse()
        self.four_factor = FourFactorModel()
        self.config = IMAW_CONFIG
    
    def run(self, ticker: str, df: pd.DataFrame, 
            regime: str = "MIXED",
            revision_data: Optional[Dict] = None) -> Dict:
        
        result = {
            "ticker": ticker,
            "timestamp": pd.Timestamp.now().isoformat(),
            "regime": regime,
        }
        
        tech = self.technical_gates.combined_score(df)
        result["phase4_technical"] = tech
        
        infra_tickers = self.opportunity.ai_infra_tickers
        result["phase2_opportunity"] = {
            "in_ai_infra": ticker in infra_tickers,
            "theme_score": 2.0 if ticker in infra_tickers else 0,
        }
        
        last = df.iloc[-1] if not df.empty else {}
        vol_z = last.get('vol_z', 0) if isinstance(last, pd.Series) else 0
        result["phase3_flow"] = {
            "volume_zscore": round(vol_z, 2) if not pd.isna(vol_z) else 0,
            "momentum_proxy": round(last.get('ROC', 0), 2) if isinstance(last, pd.Series) else 0,
        }
        
        ff = self.four_factor.score(ticker, df, revision_data)
        result["phase5_four_factor"] = ff
        
        atr = last.get('atr', df['close'].iloc[-1] * 0.02) if not df.empty else 0
        price = df['close'].iloc[-1] if not df.empty else 0
        stop = price - 2 * atr if price > 0 else 0
        target = price + 3 * atr if price > 0 else 0
        r_r = (target - price) / (price - stop) if (price - stop) > 0 else 0
        
        result["phase6_risk_reward"] = {
            "entry": round(price, 2),
            "stop": round(stop, 2),
            "target": round(target, 2),
            "risk_reward": round(r_r, 2),
            "atr": round(atr, 2) if not pd.isna(atr) else 0,
        }
        
        weights = self.config["weights"]
        total_score = (
            weights["phase1_regime_fit"] * (2.0 if regime == "RISK_ON" else 1.0 if regime == "MIXED" else 0.3) +
            weights["phase2_theme_opportunity"] * result["phase2_opportunity"]["theme_score"] +
            weights["phase3_flow_momentum"] * (1.5 if vol_z > 1.0 else 1.0) +
            weights["phase4_technical"] * tech["combined_tech_score"] +
            weights["phase5_expert_synthesis"] * (ff["total_score"] / 5) +
            weights["phase6_risk_reward"] * (2.0 if r_r > 2.0 else 1.0)
        )
        
        if tech["weekly_gate_pass"]:
            total_score *= 1.25
        
        confirmed = total_score >= self.config["scoring"]["min_confirmed_score"]
        preliminary = total_score >= self.config["scoring"]["preliminary_score_threshold"]
        
        result["phase7_signal"] = {
            "total_score": round(total_score, 2),
            "signal_type": "CONFIRMED" if confirmed else "PRELIMINARY" if preliminary else "NONE",
            "action": "BUY" if confirmed else "WATCH" if preliminary else "AVOID",
            "weekly_gate_required": tech["weekly_gate_pass"],
        }
        
        return result
    
    def run_universe(self, data: Dict[str, pd.DataFrame], 
                     regime: str = "MIXED") -> List[Dict]:
        results = []
        
        opportunities = self.opportunity.screen(data, regime)
        opp_tickers = [o['ticker'] for o in opportunities]
        
        for ticker in opp_tickers:
            df = data.get(ticker)
            if df is None or df.empty:
                continue
            
            result = self.run(ticker, df, regime)
            results.append(result)
        
        results.sort(key=lambda x: x["phase7_signal"]["total_score"], reverse=True)
        return results
