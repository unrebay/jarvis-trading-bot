#!/usr/bin/env python3
"""
JARVIS — GitHub Webhook Auto-Deploy Server

Listens for GitHub push events on the `production` branch and
automatically pulls the latest code + restarts the bot service.

No external dependencies — uses only Python stdlib.

Config (via .env or environment):
  WEBHOOK_SECRET  — GitHub webhook secret (required for security)
  WEBHOOK_PORT    — port to listen on (default: 9000)

Endpoint:  POST /deploy
"""

import hashlib
import hmac
import json
import logging
import os
import subprocess
import sys
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
        if self.path != "/deploy":
            self._respond(404, b"Not found")
            return

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
    log.info(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    log.info(f"  JARVIS Webhook Server starting")
    log.info(f"  Port   : {PORT}")
    log.info(f"  Branch : {BRANCH}")
    log.info(f"  Secret : {'✅ set' if WEBHOOK_SECRET else '⚠️  NOT SET (insecure)'}")
    log.info(f"  Script : {DEPLOY_SCRIPT}")
    log.info(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    server = HTTPServer(("0.0.0.0", PORT), WebhookHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log.info("Webhook server stopped")
