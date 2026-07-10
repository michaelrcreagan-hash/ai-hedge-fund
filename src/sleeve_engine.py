"""
4-Sleeve Portfolio Engine
Optimized parameters from grid search (OPTIMIZATION_REPORT.md)
Sleeves: Macro Rotation | Income/Hedge | Innovation/High-Conviction | Options Overlay
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

from src.config import SleeveParams, REGIME_WEIGHTS, REGIME_THRESHOLDS, LAYER_CAKE_TICKERS, FULL_UNIVERSE


class MacroSleeve:
    """Sector/theme momentum with inverse-vol weighting (trend gate OFF per optimization)"""
    
    def __init__(self, params: SleeveParams):
        self.params = params
        self.universe = ["XLK", "XLU", "XLI", "XLB", "XLF", "XLV", "XLE", 
                        "SMH", "IGV", "BOTZ", "ICLN", "PAVE", "JETS"]
    
    def compute_weights(self, data: Dict[str, pd.DataFrame], regime: str) -> Dict[str, float]:
        vols = {}
        for ticker, df in data.items():
            if ticker in self.universe and len(df) > 20:
                vol = df['close'].pct_change().rolling(20).std().iloc[-1] * np.sqrt(252)
                if vol > 0 and not np.isnan(vol):
                    vols[ticker] = vol
        
        if not vols:
            return {}
        
        inv_vols = {t: 1.0 / v for t, v in vols.items()}
        total = sum(inv_vols.values())
        weights = {t: w / total for t, w in inv_vols.items()}
        
        return weights
    
    def get_signals(self, data: Dict[str, pd.DataFrame]) -> List[Dict]:
        signals = []
        for ticker, df in data.items():
            if ticker not in self.universe or len(df) < 50:
                continue
            
            ret_63d = df['close'].iloc[-1] / df['close'].iloc[-64] - 1 if len(df) >= 64 else 0
            above_50dma = df['close'].iloc[-1] > df['close'].rolling(50).mean().iloc[-1]
            adx = df.get('ADX', pd.Series([0])).iloc[-1]
            
            score = 0
            if ret_63d > 0.05: score += 2
            if ret_63d > 0.10: score += 1
            if above_50dma: score += 2
            if adx > 20: score += 1
            
            if score >= 4:
                signals.append({
                    "ticker": ticker,
                    "score": score,
                    "return_63d": ret_63d,
                    "above_50dma": above_50dma,
                    "regime": "momentum",
                })
        
        signals.sort(key=lambda x: x['score'], reverse=True)
        return signals[:5]


class IncomeSleeve:
    """Crisis-hedge carry: TLT + GLD + PFF + GDXJ"""
    
    def __init__(self, params: SleeveParams):
        self.params = params
        self.core_holdings = ["TLT", "GLD", "PFF", "GDXJ", "IEF", "SHY"]
    
    def compute_weights(self, data: Dict[str, pd.DataFrame], 
                       spy_data: Optional[pd.DataFrame] = None) -> Dict[str, float]:
        weights = {}
        base_weight = 1.0 / len(self.core_holdings)
        for h in self.core_holdings:
            weights[h] = base_weight
        
        tlt_df = data.get("TLT")
        if tlt_df is not None and len(tlt_df) > 200:
            tlt_above_200dma = tlt_df['close'].iloc[-1] > tlt_df['close'].rolling(200).mean().iloc[-1]
            if not tlt_above_200dma:
                weights['TLT'] *= 0.5
                weights['IEF'] += weights['TLT'] * 0.3
                weights['SHY'] += weights['TLT'] * 0.2
        
        if spy_data is not None and tlt_df is not None:
            spy_ret = spy_data['close'].pct_change().dropna()
            tlt_ret = tlt_df['close'].pct_change().dropna()
            if len(spy_ret) > 60 and len(tlt_ret) > 60:
                aligned = pd.concat([spy_ret, tlt_ret], axis=1).dropna()
                if len(aligned) > 60:
                    corr = aligned.iloc[-60:].corr().iloc[0, 1]
                    if not np.isnan(corr) and corr > 0:
                        weights['GLD'] *= 1.5
                        weights['GDXJ'] *= 1.3
        
        total = sum(weights.values())
        return {k: v / total for k, v in weights.items()} if total > 0 else weights
    
    def get_signals(self, data: Dict[str, pd.DataFrame]) -> List[Dict]:
        return [{"ticker": "TLT/GLD/PFF/GDXJ", "action": "carry_allocation", 
                "regime": "defensive_core"}]


class InnovationSleeve:
    """Concentrated momentum in AI bottleneck names"""
    
    def __init__(self, params: SleeveParams):
        self.params = params
        self.universe = []
        for layer_tickers in LAYER_CAKE_TICKERS.values():
            self.universe.extend(layer_tickers)
        self.universe = list(set(self.universe))
        self.universe.extend([t for t in FULL_UNIVERSE if t not in self.universe])
        self.universe = list(set(self.universe))
    
    def compute_momentum_score(self, df: pd.DataFrame) -> float:
        if len(df) < self.params.momentum_window + 5:
            return 0.0
        
        window = self.params.momentum_window
        ret = df['close'].iloc[-1] / df['close'].iloc[-(window+1)] - 1
        vol = df['close'].pct_change().rolling(20).std().iloc[-1] * np.sqrt(252)
        
        if vol > 0 and not np.isnan(vol):
            vol_scalar = self.params.innovation_vol_target / vol
            vol_scalar = min(vol_scalar, 2.0)
        else:
            vol_scalar = 1.0
        
        score = ret * vol_scalar
        
        price = df['close'].iloc[-1]
        if price < 5:
            score = -999
        
        return score
    
    def get_top_n(self, data: Dict[str, pd.DataFrame], n: Optional[int] = None) -> List[Dict]:
        if n is None:
            n = self.params.innovation_top_n
        
        scores = []
        for ticker, df in data.items():
            if ticker not in self.universe:
                continue
            score = self.compute_momentum_score(df)
            if score > -100:
                scores.append({
                    "ticker": ticker,
                    "momentum_score": score,
                    "price": df['close'].iloc[-1] if len(df) > 0 else 0,
                })
        
        scores.sort(key=lambda x: x['momentum_score'], reverse=True)
        return scores[:n]
    
    def compute_weights(self, data: Dict[str, pd.DataFrame]) -> Dict[str, float]:
        top = self.get_top_n(data)
        if not top:
            return {}
        weight = 1.0 / len(top)
        return {t['ticker']: weight for t in top}


class OptionsSleeve:
    """Poor Man's Covered Call on SMH using LEAPS diagonal"""
    
    def __init__(self, params: SleeveParams):
        self.params = params
        self.underlying = "SMH"
    
    def get_structure(self, underlying_price: float, 
                     iv_rank: float = 50) -> Dict:
        delta = self.params.options_short_delta
        
        leaps_strike = round(underlying_price * 0.85, 0)
        leaps_expiry = "Jan 2027"
        
        short_strike = round(underlying_price * (1 + delta), 0)
        short_expiry = "30 DTE"
        
        return {
            "underlying": self.underlying,
            "strategy": "PMCC_Diagonal",
            "long_call": {"strike": leaps_strike, "expiry": leaps_expiry, "delta_target": 0.80},
            "short_call": {"strike": short_strike, "expiry": short_expiry, "delta_target": delta},
            "max_loss": underlying_price * 0.15,
            "target_annual_income_pct": 0.15,
            "roll_trigger": "When short call delta > 0.40 or 21 DTE",
            "skip_rule": "Skip short leg on hyper-momentum names",
        }
    
    def compute_weights(self, data: Dict[str, pd.DataFrame]) -> Dict[str, float]:
        return {self.underlying: 1.0}


class RegimeDetector:
    """TECE v5.2 Regime Detection"""
    
    def __init__(self):
        self.thresholds = REGIME_THRESHOLDS
    
    def detect(self, vix: Optional[float], smh_price: float, smh_200dma: float,
               dxy: Optional[float] = None, 
               spy_price: float = 0, spy_200dma: float = 0) -> str:
        
        if vix and vix > 30:
            return "RISK_OFF"
        if smh_price < smh_200dma * 0.95:
            return "RISK_OFF"
        
        risk_on = False
        risk_off = False
        
        if vix and vix < self.thresholds['risk_on_vix_max']:
            if smh_price > smh_200dma:
                risk_on = True
        
        if vix and vix > self.thresholds['risk_off_vix_min']:
            risk_off = True
        
        if risk_on:
            return "RISK_ON"
        elif risk_off:
            return "RISK_OFF"
        else:
            if smh_price > smh_200dma:
                return "MIXED"
            else:
                return "CAUTION"
    
    def compute_tece_score(self, tech_revisions: float = 2.0,
                          employment_macro: float = 2.0,
                          credit_conditions: float = 2.0,
                          equity_risk: float = 2.0) -> Tuple[int, str]:
        total = int(tech_revisions + employment_macro + credit_conditions + equity_risk)
        
        if total >= 8:
            return total, "RISK_ON"
        elif total >= 5:
            return total, "MIXED"
        elif total >= 3:
            return total, "CAUTION"
        else:
            return total, "RISK_OFF"


class FourSleevePortfolio:
    """Master portfolio engine combining all 4 sleeves with regime-based allocation"""
    
    def __init__(self, params: Optional[SleeveParams] = None):
        self.params = params or SleeveParams()
        self.macro = MacroSleeve(self.params)
        self.income = IncomeSleeve(self.params)
        self.innovation = InnovationSleeve(self.params)
        self.options = OptionsSleeve(self.params)
        self.regime = RegimeDetector()
        self.current_regime = "MIXED"
        self.positions = {}
        self.cash_pct = 0.0
    
    def update_regime(self, data: Dict[str, pd.DataFrame]) -> str:
        smh_df = data.get("SMH")
        vix_df = data.get("^VIX")
        
        smh_price = smh_df['close'].iloc[-1] if smh_df is not None and len(smh_df) > 0 else 0
        smh_200dma = smh_df['close'].rolling(200).mean().iloc[-1] if smh_df is not None and len(smh_df) > 200 else smh_price
        vix = vix_df['close'].iloc[-1] if vix_df is not None and len(vix_df) > 0 else None
        
        self.current_regime = self.regime.detect(
            vix=vix,
            smh_price=smh_price,
            smh_200dma=smh_200dma
        )
        return self.current_regime
    
    def compute_target_allocation(self) -> Dict[str, float]:
        regime_weights = REGIME_WEIGHTS.get(self.current_regime, REGIME_WEIGHTS["MIXED"])
        return regime_weights
    
    def generate_signals(self, data: Dict[str, pd.DataFrame]) -> Dict[str, List[Dict]]:
        signals = {
            "regime": self.current_regime,
            "macro": self.macro.get_signals(data),
            "income": self.income.get_signals(data),
            "innovation": self.innovation.get_top_n(data),
            "options": [],
        }
        
        smh_df = data.get("SMH")
        if smh_df is not None and len(smh_df) > 0:
            price = smh_df['close'].iloc[-1]
            iv_rank = 50
            signals["options"] = [self.options.get_structure(price, iv_rank)]
        
        return signals
    
    def compute_full_portfolio(self, data: Dict[str, pd.DataFrame],
                               spy_data: Optional[pd.DataFrame] = None) -> Dict:
        regime = self.update_regime(data)
        sleeve_weights = self.compute_target_allocation()
        
        macro_weights = self.macro.compute_weights(data, regime)
        income_weights = self.income.compute_weights(data, spy_data)
        innovation_weights = self.innovation.compute_weights(data)
        
        final = {}
        
        for ticker, weight in macro_weights.items():
            final[ticker] = final.get(ticker, 0) + weight * sleeve_weights["macro"]
        
        for ticker, weight in income_weights.items():
            final[ticker] = final.get(ticker, 0) + weight * sleeve_weights["income"]
        
        for ticker, weight in innovation_weights.items():
            final[ticker] = final.get(ticker, 0) + weight * sleeve_weights["innovation"]
        
        smh_alloc = sleeve_weights.get("options", 0.10)
        final["SMH"] = final.get("SMH", 0) + smh_alloc
        
        final["CASH"] = sleeve_weights.get("cash", 0.10)
        
        total = sum(v for k, v in final.items() if k != "CASH")
        if total > 0:
            for k in final:
                if k != "CASH":
                    final[k] /= total
                    final[k] *= (1 - final.get("CASH", 0))
        
        return {
            "regime": regime,
            "sleeve_weights": sleeve_weights,
            "holdings": final,
            "macro_signals": self.macro.get_signals(data),
            "innovation_top": self.innovation.get_top_n(data),
        }
