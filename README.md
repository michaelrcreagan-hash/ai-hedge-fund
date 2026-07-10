# AI Hedge Fund System

**AI-driven multi-sleeve hedge fund** integrating Tauric Research TradingAgents, 4-sleeve portfolio optimization, IAE 10-layer technical confluence, and 66-stock AI bottleneck universe selection.

![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

## Performance Targets

| Metric | Target |
|--------|--------|
| CAGR | **42-44%** |
| Max Drawdown | **-8.5%** |
| Sharpe | **2.5-2.7** |
| MAR | **4.5-5.0** |

## Architecture (7 Layers)

```
Layer 7: TradingAgents Multi-Agent Orchestration
Layer 6: 4-Sleeve Portfolio Allocation (Regime Matrix)
Layer 5: Omega Theme Rotation Engine
Layer 4: AI Bottleneck 66-Stock Selection (4 Tiers)
Layer 3: 6-Module Composite Scoring Engine
Layer 2: IAE 10-Layer Technical Confluence
Layer 1: Data Ingestion (YF, LSEG, TipRanks)
```

## Quick Start

```bash
git clone https://github.com/michaelrcreagan-hash/ai-hedge-fund.git
cd ai-hedge-fund
pip install -e ".[dev]"
cp .env.example .env
# Edit .env with your API keys
python -m ai_hedge_fund scan --date 2026-07-10
```

## CLI Commands

| Command | Description |
|---------|-------------|
| `scan` | Daily portfolio scan with signals |
| `rebalance` | Full sleeve rebalancing |
| `backtest` | Historical walk-forward backtest |
| `monte-carlo` | Block bootstrap stress test |
| `snapshot` | Current portfolio state |
| `status` | System health check |

## 4-Sleeve Portfolio

| Sleeve | RISK-ON | Strategy |
|--------|---------|----------|
| Macro Rotation | 40% | Cross-sectional RS ranking |
| Income/Hedge | 15% | TLT/GLD/PFF conditional |
| Innovation | 35% | 63d momentum, top-4, vol-target 0.35 |
| Options PMCC | 10% | LEAPS diagonal on SMH |

## License

MIT
