# TradingView Indicators - Options Flow Composite System

## Overview

This directory contains Pine Script v6 indicators that integrate with the AI Hedge Fund's 4-sleeve portfolio system. These indicators provide real-time composite scoring, early entry/exit detection, and multi-ETF screening capabilities.

## Indicators

### 1. OptionsFlowComposite_v6.pine - Core Composite Indicator
**Purpose**: Research-backed multi-factor trading signal generator

**Components & Weights** (optimized via backtesting 14 tickers):
| Component | Weight | Description |
|-----------|--------|-------------|
| Volume/Flow Intensity | 35% | Proxies options activity via volume patterns |
| Volatility Contraction | 30% | Detects Bollinger/Keltner squeezes before breakouts |
| Momentum (RSI+MACD) | 15% | Confirms directional bias |
| Trend Alignment | 15% | EMA structure validation |
| Mean Reversion | 5% | Contrarian oversold/overbought signals |

**Signals**:
- **Composite Score** (0-100): Bullish > 65, Bearish < 35
- **Early Entry**: Green triangles - VCP forming, potential breakout imminent
- **Early Exit**: Red triangles - Overbought exhaustion, correction likely
- **Background**: Green/Red/Neutral coloring by signal zone

**Installation**:
1. Open TradingView Pine Editor
2. Copy/paste the Pine Script code
3. Click "Add to Chart"
4. Use on Daily timeframe for best results

### 2. ETF_Master_Dashboard_v6.pine - ETF Dashboard
**Purpose**: Monitors 17 thematic ETFs in real-time with sector rotation heatmap

**Tracked ETFs**:
| ETF | Sector | Key Holdings |
|-----|--------|-------------|
| SOXX/SMH/DRAM | Semiconductors | NVDA, AMD, MU, AVGO, TSM |
| SPY/QQQ/IWM | Broad Market | AAPL, MSFT, AMZN, GOOGL |
| AIPO/UTES | AI Power & Utilities | VST, CEG, OKLO, NRG |
| BOTZ/TCAI/AIVC | AI/Robotics/Infrastructure | NVDA, TSLA, ISRG, DELL |
| XBI | Biotech | VRTX, REGN, GILD, AMGN |
| ARKF/ARKQ | Fintech & Autonomous | COIN, SQ, TSLA, AMD |
| ICLN/URA | Clean Energy & Uranium | FSLR, ENPH, CCJ, OKLO |
| WGMI | Bitcoin Mining | MSTR, RIOT, CLSK, CORZ |

**Features**:
- Live composite score table with BUY/SELL/HOLD signals
- Sector Rotation Heatmap (Semis vs AI vs Power vs Speculative)
- Market Regime Detection (Risk-On/Neutral/Risk-Off)
- Early Entry/Exit markers per ETF
- Summary counts: X of 17 ETFs bullish/bearish/early entry

### 3. Constituent_Screener_v6.pine - Stock Screener
**Purpose**: Tracks 54 highest-conviction individual stocks by ETF overlap

**Top Conviction Stocks**:
| Ticker | Conviction Score | ETFs Present |
|--------|-----------------|--------------|
| NVDA | 8 | SOXX, SMH, SPY, QQQ, ARKQ, DRAM, BOTZ, AIVC |
| AMD | 6 | SOXX, SMH, QQQ, ARKQ, DRAM, AIVC |
| MU | 6 | SOXX, SMH, QQQ, DRAM, TCAI, AIVC |
| AVGO | 5 | SOXX, SMH, SPY, QQQ, AIVC |
| AMAT | 5 | SOXX, SMH, QQQ, DRAM, AIVC |

**Features**:
- Sortable by Composite Score, Conviction, Momentum, or 5D Return
- Filterable by minimum conviction level (1-8 ETFs)
- "Early Entries Only" filter mode
- Color-coded by sector with full signal breakdown

## Research Foundation

The weighting scheme is derived from peer-reviewed studies:
- **PCA Analysis** (PMC Study): Volume (0.466), P/C Ratio (0.259), OI (0.466)
- **VCP Methodology** (Mark Minervini): 90%+ success rate with trend filter
- **Put/Call Contrarian**: Extreme spikes predict bounces with trend confirmation
- **Short Interest Dynamics** (S3 Partners): Options hedging flow mechanics

## Backtest Results (14 tickers, 2-year period)

| Metric | Result |
|--------|--------|
| Average Return | +25.2% |
| Average Win Rate | 51.0% |
| Average Max Drawdown | -7.4% |
| Average Sharpe | 1.32 |
| Average Trades | 21 |

## Integration with AI Hedge Fund

These indicators feed into the system's Layer 2 (IAE Technical Confluence) and Layer 5 (Omega Theme Rotation):

```
TradingView Indicators (Real-time)
         |
         v
+----------------------------------+
| Composite Score (0-100)          |
| Early Entry/Exit Signals         |
| Sector Rotation Data             |
+----------------------------------+
         |
         v
AI Hedge Fund CLI / GitHub Actions
         |
         v
+----------------------------------+
| Layer 6: 4-Sleeve Allocation     |
| Layer 5: Theme Rotation          |
| Layer 3: Composite Scoring       |
+----------------------------------+
```

## Free Dashboard

A free web dashboard is available at the deployed URL (see main README). It provides:
- Real-time signal tracking without TradingView subscription
- Historical backtest visualization
- Options trade identification
- Mobile-responsive design

## License

Same as parent project: MIT
