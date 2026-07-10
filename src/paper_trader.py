"""
Alpaca Paper Trading Integration
Live execution, position tracking, P&L monitoring
"""
import os
import json
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict

try:
    from alpaca.trading.client import TradingClient
    from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest
    from alpaca.trading.enums import OrderSide, TimeInForce
    from alpaca.data.historical import StockHistoricalDataClient
    from alpaca.data.requests import StockBarsRequest
    from alpaca.data.timeframe import TimeFrame
    ALPACA_AVAILABLE = True
except ImportError:
    ALPACA_AVAILABLE = False

import pandas as pd


@dataclass
class PaperPosition:
    ticker: str
    shares: int
    entry_price: float
    entry_date: str
    stop_price: float
    target_price: float
    sleeve: str
    signal_type: str
    unrealized_pnl: float = 0.0
    status: str = "OPEN"
    
    def update_pnl(self, current_price: float):
        self.unrealized_pnl = (current_price - self.entry_price) * self.shares
        if current_price <= self.stop_price:
            self.status = "STOPPED"
        elif current_price >= self.target_price:
            self.status = "TARGET"


@dataclass
class TradeRecord:
    ticker: str
    action: str
    shares: int
    price: float
    sleeve: str
    signal_type: str
    timestamp: str
    commission: float = 0.0


class PaperTrader:
    """Paper trading engine with Alpaca integration"""
    
    def __init__(self, api_key: str = None, secret_key: str = None, 
                 paper: bool = True, initial_capital: float = 50000):
        self.api_key = api_key or os.getenv("ALPACA_API_KEY", "")
        self.secret_key = secret_key or os.getenv("ALPACA_SECRET_KEY", "")
        self.paper = paper
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.positions: Dict[str, PaperPosition] = {}
        self.trade_history: List[TradeRecord] = []
        self.daily_pnl = []
        
        self.trading_client = None
        self.data_client = None
        if ALPACA_AVAILABLE and self.api_key and self.secret_key:
            try:
                self.trading_client = TradingClient(self.api_key, self.secret_key, paper=paper)
                self.data_client = StockHistoricalDataClient(self.api_key, self.secret_key)
            except Exception as e:
                print(f"[PaperTrader] Alpaca init failed: {e}")
        
        self.simulated = not (ALPACA_AVAILABLE and self.trading_client is not None)
    
    def buy(self, ticker: str, shares: int, sleeve: str = "innovation",
            signal_type: str = "IMAW", stop_price: float = 0,
            target_price: float = 0, current_price: float = 0) -> Dict:
        cost = shares * current_price
        
        if cost > self.cash:
            return {"success": False, "error": f"Insufficient cash: ${self.cash:.2f} < ${cost:.2f}"}
        
        if not self.simulated:
            try:
                order = MarketOrderRequest(
                    symbol=ticker, qty=shares, side=OrderSide.BUY, time_in_force=TimeInForce.DAY
                )
                self.trading_client.submit_order(order)
            except Exception as e:
                return {"success": False, "error": f"Alpaca error: {e}"}
        
        self.cash -= cost
        
        pos = PaperPosition(
            ticker=ticker, shares=shares, entry_price=current_price,
            entry_date=datetime.now().isoformat(), stop_price=stop_price,
            target_price=target_price, sleeve=sleeve, signal_type=signal_type,
        )
        self.positions[ticker] = pos
        
        record = TradeRecord(
            ticker=ticker, action="BUY", shares=shares, price=current_price,
            sleeve=sleeve, signal_type=signal_type, timestamp=datetime.now().isoformat(),
        )
        self.trade_history.append(record)
        
        return {
            "success": True, "ticker": ticker, "shares": shares,
            "cost": round(cost, 2), "cash_remaining": round(self.cash, 2),
            "mode": "simulated" if self.simulated else "alpaca",
        }
    
    def sell(self, ticker: str, shares: Optional[int] = None, reason: str = "signal") -> Dict:
        pos = self.positions.get(ticker)
        if not pos:
            return {"success": False, "error": f"No position in {ticker}"}
        
        sell_shares = shares or pos.shares
        if sell_shares > pos.shares:
            sell_shares = pos.shares
        
        current_price = pos.entry_price
        proceeds = sell_shares * current_price
        
        if not self.simulated:
            try:
                order = MarketOrderRequest(
                    symbol=ticker, qty=sell_shares, side=OrderSide.SELL, time_in_force=TimeInForce.DAY
                )
                self.trading_client.submit_order(order)
            except Exception:
                pass
        
        realized_pnl = (current_price - pos.entry_price) * sell_shares
        self.cash += proceeds
        
        record = TradeRecord(
            ticker=ticker, action="SELL", shares=sell_shares, price=current_price,
            sleeve=pos.sleeve, signal_type=f"{pos.signal_type}_EXIT_{reason}",
            timestamp=datetime.now().isoformat(),
        )
        self.trade_history.append(record)
        
        remaining = pos.shares - sell_shares
        if remaining <= 0:
            pos.status = "CLOSED"
            del self.positions[ticker]
        else:
            pos.shares = remaining
        
        return {
            "success": True, "ticker": ticker, "shares_sold": sell_shares,
            "proceeds": round(proceeds, 2), "realized_pnl": round(realized_pnl, 2),
            "cash": round(self.cash, 2),
        }
    
    def update_positions(self, prices: Dict[str, float]):
        for ticker, pos in list(self.positions.items()):
            price = prices.get(ticker)
            if price:
                pos.update_pnl(price)
    
    def get_portfolio_value(self, prices: Dict[str, float]) -> float:
        pos_value = sum(
            pos.shares * prices.get(ticker, pos.entry_price)
            for ticker, pos in self.positions.items()
        )
        return self.cash + pos_value
    
    def get_dashboard(self, prices: Dict[str, float] = None) -> Dict:
        total_value = self.get_portfolio_value(prices or {})
        
        positions_list = []
        for ticker, pos in self.positions.items():
            current_price = prices.get(ticker, pos.entry_price) if prices else pos.entry_price
            pos.update_pnl(current_price)
            positions_list.append({
                "ticker": ticker, "shares": pos.shares, "entry": pos.entry_price,
                "current": current_price, "unrealized_pnl": round(pos.unrealized_pnl, 2),
                "sleeve": pos.sleeve, "signal": pos.signal_type, "status": pos.status,
                "stop": pos.stop_price, "target": pos.target_price,
            })
        
        sleeve_values = {}
        for p in positions_list:
            sleeve = p["sleeve"]
            val = p["shares"] * p["current"]
            sleeve_values[sleeve] = sleeve_values.get(sleeve, 0) + val
        
        total_pos_value = sum(sleeve_values.values())
        sleeve_pcts = {s: round(v / total_value * 100, 1) if total_value > 0 else 0 
                      for s, v in sleeve_values.items()}
        
        return {
            "cash": round(self.cash, 2),
            "positions_value": round(total_pos_value, 2),
            "total_value": round(total_value, 2),
            "total_return_pct": round((total_value - self.initial_capital) / self.initial_capital * 100, 2),
            "positions": positions_list,
            "sleeve_allocation": sleeve_pcts,
            "num_positions": len(positions_list),
            "trade_count": len(self.trade_history),
            "mode": "simulated" if self.simulated else "alpaca_paper",
        }
    
    def liquidate_all(self, prices: Dict[str, float] = None) -> Dict:
        results = []
        for ticker in list(self.positions.keys()):
            result = self.sell(ticker, reason="kill_switch")
            results.append(result)
        return {"liquidated": len(results), "details": results}
