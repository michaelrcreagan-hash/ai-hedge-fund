"""
Bottleneck Capital — Web Dashboard
FastAPI + HTML/JS real-time fund monitoring
"""
import json
from datetime import datetime
from typing import Dict, Optional
from pathlib import Path

try:
    from fastapi import FastAPI, WebSocket, Request
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import HTMLResponse, JSONResponse
    from fastapi.templating import Jinja2Templates
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False

from src.orchestrator import BottleneckFundOrchestrator

app = FastAPI(title="Bottleneck Capital — Agentic Hedge Fund Dashboard")

if FASTAPI_AVAILABLE:
    templates = Jinja2Templates(directory="templates")

fund: Optional[BottleneckFundOrchestrator] = None


def init_fund(api_key: str = None, secret_key: str = None, capital: float = 50000):
    global fund
    fund = BottleneckFundOrchestrator(
        initial_capital=capital,
        alpaca_key=api_key,
        alpaca_secret=secret_key
    )
    return fund


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    if not FASTAPI_AVAILABLE:
        return HTMLResponse("<h1>FastAPI not installed. Run: pip install fastapi uvicorn</h1>")
    return templates.TemplateResponse("dashboard.html", {"request": request})


@app.get("/api/status")
async def api_status():
    if fund is None:
        return {"status": "NOT_INITIALIZED"}
    return {"status": "ACTIVE", "regime": fund.current_regime, "last_update": fund.last_update}


@app.post("/api/init")
async def api_init(capital: float = 50000):
    init_fund(capital=capital)
    return {"status": "INITIALIZED", "capital": capital}


@app.post("/api/refresh")
async def api_refresh():
    if fund is None:
        return {"error": "Fund not initialized"}
    return fund.refresh_data()


@app.post("/api/cycle")
async def api_run_cycle():
    if fund is None:
        return {"error": "Fund not initialized"}
    return fund.run_full_cycle()


@app.get("/api/dashboard")
async def api_dashboard():
    if fund is None:
        return {"error": "Fund not initialized"}
    return fund.get_full_dashboard()


@app.get("/api/regime")
async def api_regime():
    if fund is None:
        return {"error": "Fund not initialized"}
    return fund.run_regime_detection()


@app.get("/api/signals")
async def api_signals():
    if fund is None:
        return {"error": "Fund not initialized"}
    signals = fund.run_imaw_pipeline()
    return {"signals": signals[:10]}


@app.get("/api/risk")
async def api_risk():
    if fund is None:
        return {"error": "Fund not initialized"}
    return {"risk_check": fund.run_risk_check(), "dashboard": fund.risk.get_dashboard()}


@app.get("/api/portfolio")
async def api_portfolio():
    if fund is None:
        return {"error": "Fund not initialized"}
    prices = {t: df['close'].iloc[-1] for t, df in fund.universe_data.items()}
    return fund.trader.get_dashboard(prices)


@app.post("/api/liquidate")
async def api_liquidate():
    if fund is None:
        return {"error": "Fund not initialized"}
    result = fund.trader.liquidate_all()
    return {"status": "LIQUIDATED", "details": result}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        try:
            if fund:
                dashboard = fund.get_full_dashboard()
                await websocket.send_json(dashboard)
            await asyncio.sleep(30)
        except Exception as e:
            await websocket.send_json({"error": str(e)})
            break


def run_cli():
    print("=" * 80)
    print("BOTTLECK CAPITAL — AGENTIC HEDGE FUND")
    print("=" * 80)
    fund = init_fund(capital=50000)
    print("\n[1/7] Refreshing market data...")
    fund.refresh_data()
    print("[2/7] Detecting regime...")
    regime = fund.run_regime_detection()
    print(f"      Regime: {regime['regime']}")
    print("[3/7] Running IMAW pipeline...")
    signals = fund.run_imaw_pipeline()
    print(f"      Signals: {len(signals)} total")
    print("[4/7] Risk check...")
    risk = fund.run_risk_check()
    print(f"      Status: {risk['status']}")
    print("[7/7] Portfolio snapshot:")
    prices = {t: df['close'].iloc[-1] for t, df in fund.universe_data.items()}
    portfolio = fund.trader.get_dashboard(prices)
    print(f"      Cash: ${portfolio['cash']:,.2f} | Positions: {portfolio['num_positions']} | Value: ${portfolio['total_value']:,.2f}")
    return fund.get_full_dashboard()


if __name__ == "__main__":
    import asyncio
    run_cli()
