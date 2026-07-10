# GitHub Actions Deployment Guide

This guide walks you through deploying the AI Hedge Fund system using **GitHub Actions** — no local environment or server required. All execution happens in GitHub's cloud infrastructure.

---

## Prerequisites

- GitHub account
- This repository forked or pushed to your GitHub account
- API keys for data providers (see below)

---

## Repository Setup

### Step 1: Fork or Push the Repo

```bash
git remote add origin https://github.com/YOUR_USERNAME/ai-hedge-fund.git
git push -u origin main
```

### Step 2: Verify Workflows Are Visible

Go to **Actions** tab in your GitHub repo. You should see these workflows:

| Workflow | Purpose | Trigger |
|----------|---------|---------|
| **CI / CD** | Lint, test, typecheck | Push/PR to main |
| **Daily Market Scan** | Daily portfolio scan | Cron (M-F 4:30 PM ET) + Manual |
| **Portfolio Rebalance** | Monthly/weekly rebalance | Cron (1st monthly + Fri weekly) + Manual |
| **Backtest** | Historical backtest | Manual only |
| **Monte Carlo Stress Test** | Risk simulation | Manual + Weekly (Sunday) |
| **Deploy Orchestrator** | Meta workflow (status/scan/rebalance) | Manual only |

---

## Secrets Configuration

All sensitive configuration is stored in **GitHub Secrets** (not in the repo). Go to **Settings > Secrets and variables > Actions** and add these:

### Required Secrets

| Secret Name | Source | Used By |
|-------------|--------|---------|
| `TIPRANKS_API_KEY` | [tipranks.com/api](https://tipranks.com/api) | Module F (Analyst Revision Velocity) |
| `LSEG_API_KEY` | [LSEG/Refinitiv](https://developers.lseg.com) | Module F consensus data |
| `FINNHUB_API_KEY` | [finnhub.io](https://finnhub.io) | Earnings, fundamentals |

### Optional Secrets

| Secret Name | Source | Used By |
|-------------|--------|---------|
| `OPENAI_API_KEY` | [platform.openai.com](https://platform.openai.com) | TradingAgents LLM layer |
| `POLYMARKET_API_KEY` | [polymarket.com](https://polymarket.com) | Event probabilities |
| `FRED_API_KEY` | [fred.stlouisfed.org](https://fred.stlouisfed.org) | Macro data |

### How Secrets Flow

```
GitHub Secrets
     |
     v
GitHub Actions workflow
     |
     v
env: TIPRANKS_API_KEY: ${{ secrets.TIPRANKS_API_KEY }}
     |
     v
Python process reads os.environ["TIPRANKS_API_KEY"]
     |
     v
Data provider API call
```

**No secrets are ever logged, committed, or stored in artifacts.**

---

## Workflows Overview

### CI/CD Pipeline (`ci.yml`)

Runs on every push and PR. Four parallel jobs:

```
lint (ruff) ----->
test (pytest) ---> All must pass for green build
typecheck (mypy) ->
validate-config ->
```

### Daily Market Scan (`daily-scan.yml`)

```
Cron: 30 20 * * 1-5   (4:30 PM ET, Mon-Fri)

Steps:
  1. Setup Python + install package
  2. Set scan date (today or override)
  3. Run: ai-hedge-fund scan --date $DATE
  4. Upload results as artifact
  5. Generate job summary (visible in Actions UI)
  6. Alert via GitHub Issue on failure
```

### Portfolio Rebalance (`rebalance.yml`)

```
Cron: 0 1 1 * *       (1st of month, 9 PM ET)
Cron: 0 21 * * 5      (Fridays, 5 PM ET)

Steps:
  1. Pre-rebalance scan
  2. Run rebalance algorithm
  3. Upload pre-scan + rebalance artifacts
  4. Commit rebalance log to repo (optional)
  5. Generate summary
  6. Alert on failure
```

### Backtest (`backtest.yml`)

```
Trigger: workflow_dispatch only

Inputs:
  - start_date (required)
  - end_date (optional, default: today)
  - capital (optional, default: $100,000)
  - regime mode (adaptive/risk_on/risk_off/inflation/low_vol)
```

### Monte Carlo (`monte-carlo.yml`)

```
Cron: 0 6 * * 0       (Sundays, 2 AM ET)
Trigger: workflow_dispatch

Inputs:
  - paths (default: 10,000)
  - horizon in days (default: 252)
  - confidence level (default: 0.95)
```

---

## Running Your First Scan

### Via GitHub Web UI

1. Go to **Actions > Daily Market Scan**
2. Click **Run workflow** (top right)
3. Optional: enter a date (YYYY-MM-DD) or leave blank for today
4. Click **Run workflow**

### Results

After ~2-5 minutes, you'll see:

- **Job summary** on the run page (top of the workflow output)
- **Artifacts** tab with `scan-results-YYYY-MM-DD.json`
- **Step logs** showing each ticker's score and signal

---

## Scheduled Operations

All schedules use UTC time:

| Workflow | Cron (UTC) | Local (ET) | Days |
|----------|-----------|------------|------|
| Daily Scan | `30 20 * * 1-5` | 4:30 PM | Mon-Fri |
| Monthly Rebalance | `0 1 1 * *` | 9:00 PM | 1st of month |
| Weekly Rebalance | `0 21 * * 5` | 5:00 PM | Friday |
| Stress Test | `0 6 * * 0` | 2:00 AM | Sunday |

To modify schedules, edit the `cron` lines in each workflow file.

---

## Manual Operations

All workflows support `workflow_dispatch` for manual runs via the GitHub Actions UI.

### Deploy Orchestrator (Recommended)

The **Deploy Orchestrator** is the best way to run operations manually:

1. Go to **Actions > Deploy Orchestrator**
2. Click **Run workflow**
3. Choose operation: `status`, `scan`, `rebalance`, or `full-cycle`

---

## Monitoring & Alerts

### Job Summaries

Every workflow writes a formatted summary to the job page. Look for the **Summary** section at the top of each workflow run.

### Failure Alerts

When a scheduled workflow fails, a GitHub Issue is automatically created with:
- Title: `[Workflow] Failed: YYYY-MM-DD`
- Labels: `alert`, `{workflow}-failure`
- Link to the failed run

### Artifacts

| Workflow | Artifacts | Retention |
|----------|-----------|-----------|
| Daily Scan | `scan-results-{date}.json` | 30 days |
| Rebalance | `rebalance-{date}-{run}.json` | 90 days |
| Backtest | `backtest-{start}_to_{end}-{run}.json` | 90 days |
| Monte Carlo | `monte-carlo-{run}.json` | 90 days |

Download artifacts from the **Artifacts** section on any workflow run page.

---

## Troubleshooting

### Workflow Not Running

- Check **Actions > (workflow) > Enable workflow** (may be disabled on fork)
- Verify cron syntax at [crontab.guru](https://crontab.guru)
- Note: Scheduled workflows don't run until at least one commit is pushed

### API Key Errors

```
Error: TIPRANKS_API_KEY not configured
```

- Go to **Settings > Secrets and variables > Actions**
- Verify secret names match exactly (case-sensitive)
- Secrets are not available to workflows triggered by PRs from forks

### Rate Limiting

If you hit API rate limits:
- yfinance: ~2,000 requests/hour (usually sufficient)
- TipRanks: Check your plan limits
- LSEG: Check your subscription tier

The system uses built-in caching to minimize API calls.

---

## Architecture

```
+-------------------------------------------------------------+
|                      GitHub Actions                          |
|                                                              |
|  +------------------+  +------------------+                  |
|  | Daily Scan       |  | Rebalance        |                  |
|  | Cron: M-F 4:30PM |  | Cron: 1st + Fri  |                  |
|  | Manual trigger   |  | Manual trigger   |                  |
|  +--------+---------+  +--------+---------+                  |
|           |                     |                            |
|           v                     v                            |
|  +--------------------------------------------------+       |
|  | Composite Action: setup-fund                       |       |
|  | - Checkout code                                   |       |
|  | - Setup Python 3.12                               |       |
|  | - pip install -e ".[dev]"                         |       |
|  | - Validate config                                 |       |
|  +--------------------------------------------------+       |
|           |                                                  |
|           v                                                  |
|  +--------------------------------------------------+       |
|  | AI Hedge Fund CLI                                  |       |
|  | python -m ai_hedge_fund scan|rebalance|...       |       |
|  +--------------------------------------------------+       |
|           |                                                  |
|           v                                                  |
|  +--------------------------------------------------+       |
|  | GitHub Secrets Injected as Env Vars                |       |
|  | TIPRANKS_API_KEY, LSEG_API_KEY, ...               |       |
|  +--------------------------------------------------+       |
|           |                                                  |
|           v                                                  |
|  +--------------------------------------------------+       |
|  | Output: Artifacts + Job Summary + Issue Alerts     |       |
|  +--------------------------------------------------+       |
+-------------------------------------------------------------+
```

---

## Next Steps

1. [ ] Add your API keys to GitHub Secrets
2. [ ] Run a manual **Daily Market Scan** to verify
3. [ ] Review the job summary and artifacts
4. [ ] Let scheduled workflows run automatically
5. [ ] Monitor via the Actions tab and email notifications
