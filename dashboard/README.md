# AI Hedge Fund Dashboard

A free, real-time web dashboard for tracking Options Flow Composite signals across 17 thematic ETFs and 226+ individual stocks.

## Live Dashboard

**URL:** https://yx6ezir57wi4g.kimi.page

## Architecture

```
TradingView Pine Script (Alert Webhooks)
         |
         v
Supabase Edge Function: tradingview-webhook
         |
         v
Supabase PostgreSQL (signals, stock_snapshots, etf_holdings)
         |
         v
React Dashboard (real-time subscriptions via Supabase client)
```

## Features

### 5 Dashboard Tabs

| Tab | Description |
|-----|-------------|
| **Overview** | Market regime, 4 key metrics, sector rotation heatmap, top early entries, composite weights reference, TradingView integration status |
| **Screener** | 54 stocks sortable by composite score, momentum, or RSI; filterable by sector; expandable detail cards with all component scores |
| **Options Picks** | Call opportunities (bullish/early entry), put targets (oversold), and strategy parameters (delta, DTE, targets, stops) |
| **Live Signals** | Real-time signal feed from TradingView webhooks with timestamps |
| **ETFs** | All 17 ETFs with composite scores, sector classification, and top holdings |

### Key Metrics
- **Composite Score** (0-100): Weighted ensemble of volume (35%), VCP (30%), momentum (15%), trend (15%), mean reversion (5%)
- **Market Regime**: Risk-On (>60), Neutral (40-60), Risk-Off (<40)
- **Early Entry**: VCP forming before breakout
- **Early Exit**: Overbought exhaustion before correction

## Supabase Backend

### Project Details
- **Project ID:** kesqaugbzcguoxdedtxt
- **Region:** us-east-1
- **Plan:** Free tier ($0/month)

### Database Tables

#### `signals`
Stores individual trading signals from TradingView webhooks.
```
id, ticker, signal_type, composite_score, vol_score, squeeze_score,
momentum_score, trend_score, mean_rev_score, rsi, price, atr, bb_width,
vol_ratio, timeframe, source, created_at, expires_at
```

#### `stock_snapshots`
Stores daily computed composite scores for each tracked stock.
```
id, ticker, composite_score, vol_score, squeeze_score, momentum_score,
trend_score, mean_rev_score, rsi, price, signal, change_5d, change_20d,
volume_ratio, snapshot_date, created_at
```

#### `etf_holdings`
Stores ETF-to-stock mapping with 226+ records.
```
id, etf_ticker, etf_name, etf_sector, stock_ticker, created_at
```

### Edge Functions

#### `tradingview-webhook`
- **URL:** `https://kesqaugbzcguoxdedtxt.supabase.co/functions/v1/tradingview-webhook`
- **Method:** POST
- **Purpose:** Receives TradingView Pine Script alert webhooks
- **Payload:**
```json
{
  "ticker": "NVDA",
  "signal": "early_entry",
  "composite": 72.5,
  "volScore": 65.0,
  "squeezeScore": 80.0,
  "momentumScore": 70.0,
  "trendScore": 75.0,
  "meanRevScore": 45.0,
  "rsi": 68.0,
  "price": 145.20,
  "timeframe": "1d"
}
```

#### `market-data-poll`
- **URL:** `https://kesqaugbzcguoxdedtxt.supabase.co/functions/v1/market-data-poll`
- **Method:** GET
- **Purpose:** Fetches Yahoo Finance data and computes composite scores
- **Query params:** `?tickers=NVDA,AMD,MU` (optional, defaults to all 54)
- **Schedule:** Every 15 min during market hours via GitHub Actions

## TradingView Integration

### Setting Up Webhooks

1. Open your TradingView chart with the Options Flow Composite indicator
2. Click the "Alerts" button (clock icon)
3. Create a new alert:
   - **Condition:** Select the OFC v6 indicator
   - **Trigger:** "Early Entry" or any signal condition
   - **Webhook URL:** `https://kesqaugbzcguoxdedtxt.supabase.co/functions/v1/tradingview-webhook`
   - **Message:**
```json
{"ticker":"{{ticker}}","signal":"early_entry","composite":{{plot_0}},"rsi":{{plot_1}},"price":{{close}}}
```

4. The dashboard will update automatically when signals arrive

## Local Development

### Prerequisites
- Node.js 18+
- npm or yarn

### Setup
```bash
# Clone the repo
git clone https://github.com/michaelrcreagan-hash/ai-hedge-fund.git
cd ai-hedge-fund/dashboard

# Install dependencies
npm install

# Copy environment variables
cp .env.example .env
# Edit .env with your Supabase credentials

# Start dev server
npm run dev
```

### Build for Production
```bash
npm run build
```

### Deploy
The dashboard auto-deploys via the web deployment tool. To deploy manually:
```bash
npm run build
# Deploy the dist/ folder to any static hosting (Vercel, Netlify, GitHub Pages)
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 19 + TypeScript + Vite + Tailwind CSS + shadcn/ui |
| Backend | Supabase (PostgreSQL + Edge Functions) |
| Real-time | Supabase Realtime (WebSocket subscriptions) |
| Data Source | Yahoo Finance API (via Edge Function proxy) |
| Hosting | Static deployment (free tier) |
| CI/CD | GitHub Actions (scheduled polling) |

## Free Tier Limits

| Service | Free Limit |
|---------|-----------|
| Supabase Database | 500MB, unlimited API calls |
| Supabase Edge Functions | 500K invocations/month |
| Supabase Realtime | 200 concurrent connections |
| Dashboard Hosting | Unlimited (static site) |
| GitHub Actions | 2,000 minutes/month |

## License

Same as parent project: MIT
