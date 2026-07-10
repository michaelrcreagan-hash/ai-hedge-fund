"""
Data Layer: Market data fetching, caching, and technical indicators
Supports: Yahoo Finance (primary), with extensibility for Polygon/Tiingo
"""
import os
import json
import pickle
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict

import numpy as np
import pandas as pd
import yfinance as yf
import requests

# ═════════════════════════════════════════════════════════════════════════════
# CACHE MANAGER
# ═════════════════════════════════════════════════════════════════════════════

class CacheManager:
    """Disk-based cache with TTL for market data"""
    
    def __init__(self, cache_dir: str = "cache", ttl_hours: int = 1):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.ttl = timedelta(hours=ttl_hours)
    
    def _key(self, ticker: str, interval: str, period: str) -> str:
        return hashlib.md5(f"{ticker}_{interval}_{period}".encode()).hexdigest()
    
    def _path(self, key: str) -> Path:
        return self.cache_dir / f"{key}.pkl"
    
    def get(self, ticker: str, interval: str, period: str) -> Optional[pd.DataFrame]:
        key = self._key(ticker, interval, period)
        path = self._path(key)
        if not path.exists():
            return None
        mtime = datetime.fromtimestamp(path.stat().st_mtime)
        if datetime.now() - mtime > self.ttl:
            path.unlink()
            return None
        try:
            with open(path, 'rb') as f:
                return pickle.load(f)
        except Exception:
            return None
    
    def set(self, ticker: str, interval: str, period: str, df: pd.DataFrame):
        key = self._key(ticker, interval, period)
        path = self._path(key)
        with open(path, 'wb') as f:
            pickle.dump(df, f)


# ═════════════════════════════════════════════════════════════════════════════
# TECHNICAL INDICATORS
# ═════════════════════════════════════════════════════════════════════════════

class TechnicalIndicators:
    """Full technical analysis suite for IMAW Weekly Gate + Daily Gate"""
    
    def __init__(self, config: dict):
        self.cfg = config.get("technical", {})
    
    def add_all(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty or len(df) < 30:
            return df
        
        df = df.copy()
        close = df['close']
        high = df['high']
        low = df['low']
        volume = df['volume']
        
        df['ema_8'] = close.ewm(span=self.cfg.get('ema_fast', 8), adjust=False).mean()
        df['ema_21'] = close.ewm(span=self.cfg.get('ema_mid', 21), adjust=False).mean()
        df['ema_50'] = close.ewm(span=self.cfg.get('ema_slow', 50), adjust=False).mean()
        df['sma_200'] = close.rolling(200).mean()
        df['above_200sma'] = close > df['sma_200']
        
        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(self.cfg.get('rsi_period', 14)).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(self.cfg.get('rsi_period', 14)).mean()
        rs = gain / loss.replace(0, np.nan)
        df['rsi'] = 100 - (100 / (1 + rs))
        
        tr1 = high - low
        tr2 = (high - close.shift()).abs()
        tr3 = (low - close.shift()).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        df['atr'] = tr.rolling(self.cfg.get('atr_period', 14)).mean()
        df['atr_pct'] = (df['atr'] / close) * 100
        
        df['vol_avg20'] = volume.rolling(20).mean()
        df['rel_vol'] = volume / df['vol_avg20'].replace(0, np.nan)
        df['vol_z'] = (volume - df['vol_avg20']) / volume.rolling(20).std().replace(0, np.nan)
        
        adx_p = self.cfg.get('adx_period', 14)
        plus_dm = high.diff()
        minus_dm = -low.diff()
        plus_dm = plus_dm.where(plus_dm > minus_dm, 0).clip(lower=0)
        minus_dm = minus_dm.where(minus_dm > plus_dm, 0).clip(lower=0)
        tr_smooth = tr.ewm(alpha=1/adx_p, adjust=False).mean()
        plus_di = 100 * (plus_dm.ewm(alpha=1/adx_p, adjust=False).mean() / tr_smooth.replace(0, np.nan))
        minus_di = 100 * (minus_dm.ewm(alpha=1/adx_p, adjust=False).mean() / tr_smooth.replace(0, np.nan))
        dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
        df['+DI'] = plus_di
        df['-DI'] = minus_di
        df['ADX'] = dx.ewm(alpha=1/adx_p, adjust=False).mean()
        df['rob_booker_bull'] = (df['ADX'] > self.cfg.get('adx_threshold', 20)) & (df['+DI'] > df['-DI'])
        
        st_p = self.cfg.get('supertrend_period', 10)
        st_mult = self.cfg.get('supertrend_mult', 3.0)
        hl2 = (high + low) / 2
        upperband = hl2 + st_mult * df['atr']
        lowerband = hl2 - st_mult * df['atr']
        supertrend = pd.Series(index=df.index, dtype=float)
        trend = 1
        for i in range(len(df)):
            if i == 0:
                supertrend.iloc[i] = upperband.iloc[i]
                continue
            if trend == 1:
                if close.iloc[i] < lowerband.iloc[i]:
                    trend = -1
                    supertrend.iloc[i] = upperband.iloc[i]
                else:
                    supertrend.iloc[i] = max(lowerband.iloc[i], supertrend.iloc[i-1] if not pd.isna(supertrend.iloc[i-1]) else lowerband.iloc[i])
            else:
                if close.iloc[i] > upperband.iloc[i]:
                    trend = 1
                    supertrend.iloc[i] = lowerband.iloc[i]
                else:
                    supertrend.iloc[i] = min(upperband.iloc[i], supertrend.iloc[i-1] if not pd.isna(supertrend.iloc[i-1]) else upperband.iloc[i])
        df['SuperTrend'] = supertrend
        df['SuperTrend_bull'] = close > df['SuperTrend']
        
        stoch_k = self.cfg.get('stoch_k', 14)
        stoch_d = self.cfg.get('stoch_d', 3)
        low_min = low.rolling(stoch_k).min()
        high_max = high.rolling(stoch_k).max()
        df['%K'] = 100 * (close - low_min) / (high_max - low_min).replace(0, np.nan)
        df['%D'] = df['%K'].rolling(stoch_d).mean()
        df['stoch_bull_cross'] = (df['%K'] > df['%D']) & (df['%K'].shift(1) <= df['%D'].shift(1))
        df['stoch_oversold'] = df['%K'] < 20
        
        df['ROC'] = 100 * (close / close.shift(self.cfg.get('roc_period', 10)) - 1)
        
        atr_sma = df['atr'].rolling(20).mean()
        df['vol_expansion'] = (df['atr'] / atr_sma.replace(0, np.nan)) > self.cfg.get('vol_expansion_ratio', 1.2)
        df['vol_contraction'] = (df['atr'] / atr_sma.replace(0, np.nan)) < 0.8
        
        obv = (volume * np.sign(close.diff())).cumsum()
        df['OBV'] = obv
        df['OBV_trend'] = df['OBV'] > df['OBV'].rolling(self.cfg.get('obv_ma_period', 20)).mean()
        
        bb_basis = close.rolling(self.cfg.get('bb_length', 20)).mean()
        bb_stdev = close.rolling(self.cfg.get('bb_length', 20)).std()
        df['bb_upper'] = bb_basis + self.cfg.get('bb_mult', 2.0) * bb_stdev
        df['bb_lower'] = bb_basis - self.cfg.get('bb_mult', 2.0) * bb_stdev
        df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / bb_basis.replace(0, np.nan) * 100
        df['bb_squeeze'] = df['bb_width'] < df['bb_width'].rolling(20).mean() * 0.8
        
        ema12 = close.ewm(span=12, adjust=False).mean()
        ema26 = close.ewm(span=26, adjust=False).mean()
        df['macd_line'] = ema12 - ema26
        df['macd_signal'] = df['macd_line'].ewm(span=9, adjust=False).mean()
        df['macd_hist'] = df['macd_line'] - df['macd_signal']
        df['macd_bullish'] = (df['macd_line'] > df['macd_signal']) & (df['macd_hist'] > 0)
        
        df['donchian_20_high'] = high.rolling(20).max()
        df['donchian_20_low'] = low.rolling(20).min()
        df['donchian_55_high'] = high.rolling(55).max()
        df['donchian_55_low'] = low.rolling(55).min()
        
        df['52w_high'] = high.rolling(252).max()
        df['52w_low'] = low.rolling(252).min()
        df['new_52w_high'] = high >= df['52w_high'].shift(1)
        df['new_52w_low'] = low <= df['52w_low'].shift(1)
        
        df['price_change_63d'] = close.pct_change(63)
        df['price_change_126d'] = close.pct_change(126)
        df['price_change_252d'] = close.pct_change(252)
        
        return df.dropna()


# ═════════════════════════════════════════════════════════════════════════════
# MARKET DATA FETCHER
# ═════════════════════════════════════════════════════════════════════════════

class MarketDataFetcher:
    """Unified market data fetcher with caching"""
    
    def __init__(self, cache_dir: str = "cache", cache_ttl_hours: int = 1):
        self.cache = CacheManager(cache_dir, cache_ttl_hours)
        self.indicators = TechnicalIndicators({})
    
    def fetch(self, ticker: str, interval: str = "1d", period: str = "6mo",
              with_indicators: bool = True) -> pd.DataFrame:
        cached = self.cache.get(ticker, interval, period)
        if cached is not None:
            if with_indicators and 'rsi' not in cached.columns:
                cached = self.indicators.add_all(cached)
            return cached
        
        try:
            df = yf.download(ticker, period=period, interval=interval, 
                           progress=False, auto_adjust=True)
            if df.empty:
                return pd.DataFrame()
            
            df = df.rename(columns=str.lower)
            if 'adj close' in df.columns:
                df = df.rename(columns={'adj close': 'close'})
            
            cols = ['open', 'high', 'low', 'close', 'volume']
            available = [c for c in cols if c in df.columns]
            df = df[available].dropna()
            
            if 'volume' in df.columns:
                df['volume'] = df['volume'].astype(float)
            
            if with_indicators:
                df = self.indicators.add_all(df)
            
            self.cache.set(ticker, interval, period, df)
            return df
            
        except Exception as e:
            print(f"  [Error] Fetching {ticker}: {e}")
            return pd.DataFrame()
    
    def fetch_multi_timeframe(self, ticker: str) -> Dict[str, pd.DataFrame]:
        daily = self.fetch(ticker, "1d", "1y")
        hourly = self.fetch(ticker, "1h", "60d")
        return {"daily": daily, "hourly": hourly}
    
    def fetch_batch(self, tickers: List[str], interval: str = "1d", 
                    period: str = "6mo") -> Dict[str, pd.DataFrame]:
        results = {}
        for t in tickers:
            df = self.fetch(t, interval, period)
            if not df.empty:
                results[t] = df
        return results
    
    def fetch_vix(self) -> Optional[float]:
        df = self.fetch("^VIX", "1d", "5d", with_indicators=False)
        if not df.empty:
            return float(df['close'].iloc[-1])
        return None
    
    def fetch_benchmarks(self) -> Dict[str, float]:
        benchmarks = {}
        for ticker in ["SPY", "QQQ", "SMH", "GLD", "TLT", "DXY"]:
            df = self.fetch(ticker, "1d", "5d", with_indicators=False)
            if not df.empty:
                benchmarks[ticker] = float(df['close'].iloc[-1])
        vix = self.fetch_vix()
        if vix:
            benchmarks['VIX'] = vix
        return benchmarks
