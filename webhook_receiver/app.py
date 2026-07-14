"""
TradingView OFC v6 -> ai-hedge-fund webhook receiver (read-only signal ledger).

Flow:
    TradingView OFC v6 alert (JSON POST, secret in URL/header)
        -> this receiver (hosted on Vercel/Railway/etc.)
        -> writes the signal to signals/<date>/<ts>_<SYM>_<ACTION>.json
           on a dedicated `signals` branch via the GitHub Contents API.

`main` is NEVER touched. The receiver only needs a GitHub token with
`contents: write` on the target repo.

This receiver does NOT trade. It only records signals for research/audit.
"""

import os
import json
import hmac
import hashlib
import datetime

from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

TV_SECRET = os.environ.get("TV_WEBHOOK_SECRET", "")
GH_TOKEN = os.environ.get("GH_TOKEN", "")
GH_REPO = os.environ.get("GH_REPO", "michaelrcreagan-hash/ai-hedge-fund")
SIGNALS_BRANCH = os.environ.get("SIGNALS_BRANCH", "signals")
DRY_RUN = os.environ.get("DRY_RUN", "").lower() in ("1", "true", "yes")

REQUIRED_KEYS = ["indicator", "symbol", "action"]


def verify_secret(req) -> bool:
    """TradingView cannot HMAC-sign webhooks, so the shared secret travels in the
    URL (?secret=) or an X_TV_SECRET header. TLS protects it in transit."""
    if not TV_SECRET:
        return True  # dev / no-secret mode
    provided = req.args.get("secret") or req.headers.get("X_TV_SECRET") or ""
    return hmac.compare_digest(provided, TV_SECRET)


def _github(headers):
    return f"https://api.github.com/repos/{GH_REPO}", headers


def commit_signal(payload: dict) -> str:
    """Commit the signal JSON to SIGNALS_BRANCH via the GitHub git-data API.
    Returns the repo-relative path of the written file."""
    api, headers = _github({
        "Authorization": f"Bearer {GH_TOKEN}",
        "Accept": "application/vnd.github+json",
    })

    sym = str(payload.get("symbol", "UNKNOWN")).replace("/", "-").replace("\\", "-")
    action = str(payload.get("action", "SIGNAL")).replace("/", "-").replace("\\", "-")
    now = datetime.datetime.now(datetime.timezone.utc)
    path = f"signals/{now.strftime('%Y/%m/%d')}/{now.strftime('%H%M%S')}_{sym}_{action}.json"
    content = json.dumps(payload, indent=2)

    if DRY_RUN:
        print(f"[DRY_RUN] would write {path}:\n{content}")
        return path

    # 1) Resolve base sha of the signals branch (create from main if missing)
    r = requests.get(f"{api}/git/refs/heads/{SIGNALS_BRANCH}", headers=headers, timeout=15)
    if r.status_code == 200:
        base_sha = r.json()["object"]["sha"]
    elif r.status_code == 404:
        main_sha = requests.get(f"{api}/git/refs/heads/main", headers=headers, timeout=15).json()["object"]["sha"]
        requests.post(f"{api}/git/refs", headers=headers,
                      json={"ref": f"refs/heads/{SIGNALS_BRANCH}", "sha": main_sha}, timeout=15)
        base_sha = main_sha
    else:
        raise RuntimeError(f"resolve base failed {r.status_code}: {r.text[:200]}")

    base_tree = requests.get(f"{api}/git/commits/{base_sha}", headers=headers, timeout=15).json()["tree"]["sha"]
    blob = requests.post(f"{api}/git/blobs", headers=headers,
                         json={"content": content, "encoding": "utf-8"}, timeout=15).json()
    new_tree = requests.post(f"{api}/git/trees", headers=headers,
                             json={"base_tree": base_tree, "tree": [
                                 {"path": path, "mode": "100644", "type": "blob", "sha": blob["sha"]}
                             ]}, timeout=15).json()
    commit = requests.post(f"{api}/git/commits", headers=headers,
                           json={"message": f"signal: {action} {sym}",
                                 "tree": new_tree["sha"], "parents": [base_sha]}, timeout=15).json()
    requests.patch(f"{api}/git/refs/heads/{SIGNALS_BRANCH}", headers=headers,
                   json={"sha": commit["sha"], "force": False}, timeout=15)
    return path


@app.get("/")
def health():
    return jsonify(ok=True, service="ofc-webhook-receiver", dry_run=DRY_RUN)


@app.post("/webhook")
def webhook():
    if not verify_secret(request):
        return jsonify(ok=False, error="unauthorized"), 401

    raw = request.get_data(as_text=True)
    try:
        payload = request.get_json(force=True, silent=True) or json.loads(raw or "{}")
    except Exception:
        return jsonify(ok=False, error="invalid JSON body"), 400

    if not isinstance(payload, dict) or any(k not in payload for k in REQUIRED_KEYS):
        return jsonify(ok=False, error=f"missing one of {REQUIRED_KEYS}"), 422

    try:
        path = commit_signal(payload)
    except Exception as exc:  # surface for debugging, never crash silently
        return jsonify(ok=False, error=f"commit failed: {exc}"), 502

    return jsonify(ok=True, path=path, symbol=payload.get("symbol"),
                   action=payload.get("action")), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port)
