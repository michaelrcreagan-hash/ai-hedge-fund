# TradingView OFC v6 → ai-hedge-fund Live Signal Ledger

**Paper-only / research use.** This wires TradingView's **Options Flow Composite v6** indicator
alerts into the repo as a permanent, version-controlled signal ledger. It does **not** place
trades — it only records alerts for research, backtest labeling, and audit.

```
TradingView OFC v6  (alert → webhook URL)
        │  POST application/json  (+ ?secret=)
        ▼
Webhook Receiver  (webhook_receiver/app.py)
        │  GitHub Contents API
        ▼
signals/<YYYY>/<MM>/<DD>/<HHMMSS>_<SYM>_<ACTION>.json
        (on the dedicated `signals` branch — main is never touched)
```

---

## 1. TradingView side (the indicator)

The OFC v6 Pine script (`tradingview_indicators/OptionsFlowComposite_v6.pine`) now includes
`alert()` calls that POST a structured JSON body. To activate:

1. Open TradingView → Pine Editor → paste the `.pine` file → **Add to Chart**.
2. Right-click the chart (or clock icon) → **Add Alert**.
3. Condition = `Options Flow Composite v6.0` → pick the event:
   - `OFC v6: EARLY_ENTRY`, `EARLY_EXIT`, `BULLISH`, or `BEARISH`.
4. In the alert dialog, enable **🔗 Webhook URL** and paste your receiver endpoint:
   ```
   https://<your-host>/webhook?secret=YOUR_TV_SECRET
   ```
5. (Optional) the **Notifications** tab can also fire the human-readable `alertcondition`
   messages if you prefer email/push instead of webhook.

The JSON body TradingView sends looks like:
```json
{
  "indicator": "OFC_v6", "symbol": "NVDA", "action": "BULLISH",
  "composite": "72.40", "vol_score": "88.0", "vcp_score": "90.0",
  "momentum_score": "71.0", "trend_score": "100.0", "meanrev_score": "30.0",
  "rsi": "68.0", "atr_pct": "3.21", "close": "128.45",
  "long_stop": "119.80", "long_tp": "145.30", "short_stop": "137.10",
  "short_tp": "111.60", "interval": "D"
}
```

---

## 2. Deploy the receiver

Required env vars (see `.env.example`):

| Var | Purpose |
|-----|---------|
| `TV_WEBHOOK_SECRET` | Shared secret checked against `?secret=` / `X_TV_SECRET`. Set it! |
| `GH_TOKEN` | GitHub PAT with **Contents: Read & Write** on the repo. |
| `GH_REPO` | `michaelrcreagan-hash/ai-hedge-fund` |
| `SIGNALS_BRANCH` | `signals` (where signal JSON files land) |
| `DRY_RUN` | `true` to log without committing (local testing) |

### Vercel
```bash
cd webhook_receiver
vercel --prod
# set env vars in the Vercel dashboard or: vercel env add
```
`vercel.json` is included.

### Railway / Render / fly.io
```bash
cd webhook_receiver
pip install -r requirements.txt
gunicorn app:app --bind 0.0.0.0:$PORT
```
`Procfile` is included.

---

## 3. Repo setup (one time)

The receiver needs a `signals` branch (auto-created from `main` on first commit if missing).
GitHub token scopes required: **Contents: Read & Write** (classic `repo`, or fine-grained
Workflows not needed — we only write signal JSON, no workflows).

Add to `Settings → Secrets and variables → Actions` if you wire any CI around signals:
none required for the receiver itself (it uses `GH_TOKEN` at runtime, not Actions).

---

## 4. Local dry-run test (no GitHub writes)

```bash
cd webhook_receiver
pip install -r requirements.txt
export DRY_RUN=true TV_WEBHOOK_SECRET=test123
python app.py
# in another shell:
curl -X POST "http://localhost:5000/webhook?secret=test123" \
  -H "Content-Type: application/json" \
  -d '{"indicator":"OFC_v6","symbol":"NVDA","action":"BULLISH","composite":"72.4"}'
# -> {"ok":true,"path":"signals/.../..._NVDA_BULLISH.json",...}
# the app prints the would-be file + content to stdout (DRY_RUN).
```

---

## 5. Security notes

- TradingView webhooks cannot be HMAC-signed; the secret rides in the URL over TLS.
  Treat it as a low-value shared secret (anyone with it can write *signal files only*).
- The token has **write to the `signals` branch only in practice** (it can technically
  write anywhere the PAT allows — scope it to this repo, fine-grained, and rotate often).
- This ledger is **read-only research data**. No order execution happens anywhere in this repo.
