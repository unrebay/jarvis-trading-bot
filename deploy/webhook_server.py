#!/usr/bin/env python3
"""
JARVIS — Webhook Server (GitHub Deploy + TradingView Alerts)

Endpoints:
  GET  /health   — liveness check
  POST /deploy   — GitHub push event → auto-deploy (HMAC-SHA256 verified)
  POST /alert    — TradingView alert → sends annotated chart to Telegram users

No external dependencies — pure Python stdlib.

Config (via /opt/jarvis/.env):
  WEBHOOK_SECRET     — GitHub webhook HMAC secret
  WEBHOOK_PORT       — port (default: 9000)
  TELEGRAM_BOT_TOKEN — bot token for sending TV alert messages
  SUPABASE_URL       — Supabase project URL
  SUPABASE_KEY       — Supabase service role key

TradingView Alert JSON format (set in Pine Script alert message):
  {
    "symbol":    "{{ticker}}",
    "timeframe": "{{interval}}",
    "action":    "{{strategy.order.action}}",
    "price":     {{close}},
    "message":   "{{strategy.order.comment}}"
  }
  Payload URL: http://77.110.126.107:9000/alert
"""

import hashlib
import hmac
import json
import logging
import os
import subprocess
import sys
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

# ── Logging ──────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [webhook] %(levelname)s %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("/var/log/jarvis-webhook.log", mode="a"),
    ],
)
log = logging.getLogger(__name__)

# ── Config ───────────────────────────────────────────────────────────────────

# Load .env from /opt/jarvis/.env if present
_env_path = Path("/opt/jarvis/.env")
if _env_path.exists():
    for line in _env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "").encode()
PORT           = int(os.getenv("WEBHOOK_PORT", "9000"))
DEPLOY_SCRIPT  = str(Path(__file__).parent / "webhook-deploy.sh")
BRANCH         = "production"

# TradingView alert config (no secret needed — alerts come from TV servers)
TELEGRAM_TOKEN  = os.getenv("TELEGRAM_BOT_TOKEN", "")
SUPABASE_URL    = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY    = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY", "")


# ── TradingView alert helpers ─────────────────────────────────────────────────

def _get_alert_subscribers(symbol: str) -> list:
    """Query Supabase for users who have this symbol in their watchlist."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        return []
    try:
        url = f"{SUPABASE_URL}/rest/v1/user_watchlist?symbol=eq.{symbol}&active=eq.true&select=telegram_id"
        req = urllib.request.Request(url, headers={
            "apikey":        SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
        })
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        log.warning(f"Supabase watchlist query failed: {e}")
        return []


def _send_telegram_message(chat_id: int, text: str) -> None:
    """Send a plain text message via Telegram Bot API (stdlib only)."""
    if not TELEGRAM_TOKEN:
        log.warning("TELEGRAM_BOT_TOKEN not set — cannot send alert message")
        return
    try:
        url  = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        data = json.dumps({"chat_id": chat_id, "text": text}).encode()
        req  = urllib.request.Request(url, data=data,
                                       headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        log.warning(f"Telegram sendMessage failed (chat {chat_id}): {e}")


# ── Signature Verification ───────────────────────────────────────────────────

def _verify_signature(payload: bytes, sig_header: str) -> bool:
    """Validate HMAC-SHA256 signature from GitHub."""
    if not WEBHOOK_SECRET:
        log.warning("WEBHOOK_SECRET not set — accepting all requests (insecure!)")
        return True
    if not sig_header or not sig_header.startswith("sha256="):
        return False
    expected = "sha256=" + hmac.new(WEBHOOK_SECRET, payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, sig_header)


# ── Handler ──────────────────────────────────────────────────────────────────

class WebhookHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        """Health-check endpoint."""
        if self.path == "/health":
            self._respond(200, b"JARVIS webhook OK")
        else:
            self._respond(404, b"Not found")

    def do_POST(self):
        if self.path == "/alert":
            self._handle_tv_alert()
        elif self.path == "/deploy":
            self._handle_deploy()
        else:
            self._respond(404, b"Not found")

    def _handle_tv_alert(self):
        """
        Receive TradingView alert JSON and forward to subscribed Telegram users.

        TV Alert message format (JSON):
          {"symbol": "BTCUSDT", "timeframe": "4h", "action": "BUY",
           "price": 85000, "message": "FVG filled, OB reached"}
        """
        length  = int(self.headers.get("Content-Length", 0))
        payload = self.rfile.read(length)

        try:
            data = json.loads(payload)
        except (json.JSONDecodeError, ValueError):
            log.warning("TV alert: bad JSON payload")
            self._respond(400, b"Bad JSON")
            return

        symbol    = str(data.get("symbol", "")).upper()
        timeframe = str(data.get("timeframe", "4h")).lower()
        action    = str(data.get("action", "")).upper()
        price     = data.get("price", "")
        message   = str(data.get("message", ""))

        log.info(f"📡 TV Alert: {symbol} {timeframe} {action} @ {price} — '{message}'")
        self._respond(200, b"Alert received")

        # Find subscribers and notify them
        subscribers = _get_alert_subscribers(symbol)
        if not subscribers:
            log.info(f"  No subscribers for {symbol}")
            return

        log.info(f"  Notifying {len(subscribers)} subscriber(s)...")
        for row in subscribers:
            chat_id = row.get("telegram_id")
            if not chat_id:
                continue
            # Build alert notification text
            action_emoji = {"BUY": "🟢", "SELL": "🔴", "LONG": "🟢", "SHORT": "🔴"}.get(action, "📡")
            text = (
                f"{action_emoji} АЛЕРТ: {symbol} · {timeframe.upper()}\n"
                + (f"Цена: {price}\n" if price else "")
                + (f"Действие: {action}\n" if action else "")
                + (f"\n{message}" if message else "")
                + f"\n\n💡 /chart {symbol} {timeframe} — смотреть чарт"
            )
            _send_telegram_message(chat_id, text)

    def _handle_deploy(self):

        # Read body
        length  = int(self.headers.get("Content-Length", 0))
        payload = self.rfile.read(length)

        # Verify signature
        sig = self.headers.get("X-Hub-Signature-256", "")
        if not _verify_signature(payload, sig):
            log.warning("❌ Invalid GitHub signature — request rejected")
            self._respond(403, b"Invalid signature")
            return

        # Parse JSON
        try:
            data = json.loads(payload)
        except (json.JSONDecodeError, ValueError):
            self._respond(400, b"Bad JSON")
            return

        ref = data.get("ref", "")

        # Only deploy production branch
        if ref != f"refs/heads/{BRANCH}":
            log.info(f"⏭  Push to {ref!r} — not {BRANCH!r}, ignoring")
            self._respond(200, b"Not production branch — ignored")
            return

        commit_msg = (data.get("head_commit") or {}).get("message", "—")[:80]
        pusher     = (data.get("pusher") or {}).get("name", "unknown")
        log.info(f"🚀 Deploy triggered by {pusher!r}: {commit_msg!r}")

        # Acknowledge immediately, then deploy in background
        self._respond(200, b"Deploy triggered")

        subprocess.Popen(
            ["bash", DEPLOY_SCRIPT],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )

    def _respond(self, code: int, body: bytes) -> None:
        self.send_response(code)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):  # suppress default noisy log
        log.debug(f"{self.address_string()} — {fmt % args}")


# ── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    log.info(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    log.info(f"  JARVIS Webhook Server starting")
    log.info(f"  Port      : {PORT}")
    log.info(f"  Branch    : {BRANCH}")
    log.info(f"  Secret    : {'✅ set' if WEBHOOK_SECRET else '⚠️  NOT SET (insecure)'}")
    log.info(f"  Script    : {DEPLOY_SCRIPT}")
    log.info(f"  TG Token  : {'✅ set' if TELEGRAM_TOKEN else '⚠️  not set (alerts disabled)'}")
    log.info(f"  Supabase  : {'✅ set' if SUPABASE_URL else '⚠️  not set (alerts disabled)'}")
    log.info(f"  Endpoints : POST /deploy  POST /alert  GET /health")
    log.info(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    server = HTTPServer(("0.0.0.0", PORT), WebhookHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log.info("Webhook server stopped")
