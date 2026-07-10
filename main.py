#!/usr/bin/env python3
"""
Bottleneck Capital — Agentic Hedge Fund
Main Entry Point

Usage:
    python main.py                      # Run single cycle (CLI mode)
    python main.py --server             # Start web dashboard
    python main.py --server --port 8080 # Start on custom port
    python main.py --init --capital 100000  # Initialize with $100k

Environment Variables:
    ALPACA_API_KEY      - Alpaca API key (optional, uses simulation if not set)
    ALPACA_SECRET_KEY   - Alpaca secret key
"""
import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.orchestrator import BottleneckFundOrchestrator


def main():
    parser = argparse.ArgumentParser(description="Bottleneck Capital — Agentic Hedge Fund")
    parser.add_argument("--server", action="store_true", help="Start web dashboard server")
    parser.add_argument("--port", type=int, default=8000, help="Server port (default: 8000)")
    parser.add_argument("--capital", type=float, default=50000, help="Initial capital (default: $50,000)")
    parser.add_argument("--cycle", action="store_true", help="Run single cycle and exit")
    parser.add_argument("--continuous", action="store_true", help="Run continuous cycles")
    parser.add_argument("--interval", type=int, default=3600, help="Cycle interval in seconds")
    args = parser.parse_args()

    alpaca_key = os.getenv("ALPACA_API_KEY")
    alpaca_secret = os.getenv("ALPACA_SECRET_KEY")
    
    if not alpaca_key:
        print("[INFO] No ALPACA_API_KEY found — running in SIMULATED mode")

    print(f"\n{'='*80}")
    print(f"  BOTTLENECK CAPITAL v2.0 — AGENTIC HEDGE FUND")
    print(f"  Initial Capital: ${args.capital:,.2f}")
    print(f"  Mode: {'ALPACA PAPER' if alpaca_key else 'SIMULATED'}")
    print(f"{'='*80}\n")

    fund = BottleneckFundOrchestrator(
        initial_capital=args.capital,
        alpaca_key=alpaca_key,
        alpaca_secret=alpaca_secret
    )

    if args.server:
        try:
            import uvicorn
            from src.dashboard import app, init_fund
            init_fund(alpaca_key, alpaca_secret, args.capital)
            print(f"[SERVER] Starting dashboard on http://localhost:{args.port}")
            uvicorn.run(app, host="0.0.0.0", port=args.port)
        except ImportError:
            print("[ERROR] FastAPI/uvicorn not installed. Run: pip install fastapi uvicorn")
            sys.exit(1)

    elif args.continuous:
        import time
        print(f"[CONTINUOUS] Running cycles every {args.interval}s")
        try:
            while True:
                result = fund.run_full_cycle()
                print(f"[CYCLE] {result['regime']['regime']} | Confirmed: {result['signals']['confirmed']} | Status: {result['risk']['status']}")
                time.sleep(args.interval)
        except KeyboardInterrupt:
            print("\n[CONTINUOUS] Stopped by user")

    else:
        result = fund.run_full_cycle()
        port = result['portfolio']
        print(f"\nPortfolio: ${port['total_value']:,.2f} ({port['total_return_pct']:+.2f}%) | Cash: ${port['cash']:,.2f} | Positions: {port['num_positions']}")


if __name__ == "__main__":
    main()
