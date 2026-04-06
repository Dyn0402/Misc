"""
login_server.py — Flask server for CERN credential collection and live status
broadcasting to the user's phone browser.

Public API:
    LoginServer(port, creds_file, plot_path)
        .start(on_ready)            → starts server, returns URL
        .wait_for_credentials()     → blocks until form submitted, returns dict
        .push_status(text, kind)    → push a line to the SSE status feed
        .reset()                    → clear pending creds (for login retry)
        .shutdown()                 → stop the server

    collect_credentials(...)        → convenience one-shot wrapper (legacy)
"""

import json
import logging
import socket
import threading
import time
import urllib.request
from pathlib import Path

from flask import Flask, request, Response, send_file as flask_send_file
from werkzeug.serving import make_server

log = logging.getLogger(__name__)

# ── Shared CSS (injected into login form pages) ────────────────────────────────

_SHARED_CSS = """
    *, *::before, *::after { box-sizing: border-box; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: #f0f4f8;
      margin: 0;
      padding: 24px 16px;
      min-height: 100vh;
    }
    .card {
      background: #fff;
      border-radius: 12px;
      box-shadow: 0 2px 12px rgba(0,0,0,0.10);
      max-width: 420px;
      margin: 0 auto;
      padding: 28px 24px 32px;
    }
    h2 { margin: 0 0 6px; font-size: 1.4rem; color: #1a1a2e; }
    .subtitle { color: #555; font-size: 0.9rem; margin: 0 0 20px; }
    .notice {
      background: #fff8e1;
      border-left: 4px solid #f59e0b;
      border-radius: 4px;
      padding: 10px 12px;
      font-size: 0.85rem;
      color: #555;
      margin-bottom: 22px;
      line-height: 1.5;
    }
    .notice strong { color: #333; }
    .field { margin-bottom: 18px; }
    label {
      display: block;
      font-size: 0.85rem;
      font-weight: 600;
      color: #333;
      margin-bottom: 6px;
      letter-spacing: 0.02em;
    }
    input[type="text"],
    input[type="password"],
    input[type="number"] {
      width: 100%;
      padding: 13px 14px;
      font-size: 1rem;
      border: 1.5px solid #d1d5db;
      border-radius: 8px;
      outline: none;
      transition: border-color 0.15s;
      -webkit-appearance: none;
    }
    input:focus { border-color: #0066cc; }
    .totp-wrap input {
      letter-spacing: 0.25em;
      font-size: 1.3rem;
      font-weight: 700;
      text-align: center;
    }
    button[type="submit"] {
      width: 100%;
      padding: 15px;
      background: #0066cc;
      color: #fff;
      font-size: 1.05rem;
      font-weight: 600;
      border: none;
      border-radius: 8px;
      cursor: pointer;
      margin-top: 6px;
      transition: background 0.15s;
      -webkit-appearance: none;
    }
    button[type="submit"]:active { background: #0052a3; }
    .plot-preview {
      width: 100%;
      margin-top: 20px;
      border-radius: 8px;
      border: 1px solid #e5e7eb;
      display: none;
    }
"""

# Availability plot image tag — shown at the bottom of login form pages.
# onerror hides it silently if no plot has been saved yet.
_PLOT_IMG = (
    '<img class="plot-preview" src="/plot.png" '
    'onload="this.style.display=\'block\'" onerror="this.style.display=\'none\'">'
)

# ── Login form pages (pre-formatted with CSS at module load) ───────────────────

# Full form: username + password + TOTP
_FORM_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>CERN Login</title>
  <style>{css}</style>
</head>
<body>
  <div class="card">
    <h2>CERN Hostel Login</h2>
    <p class="subtitle">Session expired — enter your credentials below.</p>
    <div class="notice">
      Get your <strong>Google Authenticator code last</strong>, just before
      tapping Submit — TOTP codes expire after 30 seconds.
    </div>
    <form method="post" autocomplete="on">
      <div class="field">
        <label for="username">CERN Username</label>
        <input id="username" name="username" type="text"
          autocomplete="username" autocorrect="off" autocapitalize="none"
          spellcheck="false" required autofocus>
      </div>
      <div class="field">
        <label for="password">Password</label>
        <input id="password" name="password" type="password"
          autocomplete="current-password" required>
      </div>
      <div class="field">
        <label for="totp">Google Authenticator Code</label>
        <div class="totp-wrap">
          <input id="totp" name="totp" type="number"
            inputmode="numeric" pattern="[0-9]{{6}}"
            maxlength="6" placeholder="000000" required>
        </div>
      </div>
      <button type="submit">Submit &amp; Log In</button>
    </form>
    {plot_img}
  </div>
</body>
</html>""".format(css=_SHARED_CSS, plot_img=_PLOT_IMG)

# TOTP-only form — shown when username/password are pre-loaded from creds file.
# {username} and {password} are filled in at request time via str.replace().
_TOTP_ONLY_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>CERN 2FA</title>
  <style>{css}</style>
</head>
<body>
  <div class="card">
    <h2>CERN Hostel — 2FA</h2>
    <p class="subtitle">Credentials loaded. Enter your Google Authenticator code.</p>
    <div class="notice">
      Open your authenticator app <strong>last</strong>, just before tapping
      Submit — TOTP codes expire after 30 seconds.
    </div>
    <form method="post" autocomplete="off">
      <input type="hidden" name="username" value="{{username}}">
      <input type="hidden" name="password" value="{{password}}">
      <div class="field">
        <label for="totp">Google Authenticator Code</label>
        <div class="totp-wrap">
          <input id="totp" name="totp" type="number"
            inputmode="numeric" pattern="[0-9]{{6}}"
            maxlength="6" placeholder="000000" required autofocus>
        </div>
      </div>
      <button type="submit">Submit &amp; Log In</button>
    </form>
    {plot_img}
  </div>
</body>
</html>""".format(css=_SHARED_CSS, plot_img=_PLOT_IMG)

# ── Status page (shown immediately after form submit; streams live updates) ────
# Inline CSS — no .format() call needed so braces don't need escaping.

_STATUS_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>CERN Hostel — Status</title>
  <style>
    *, *::before, *::after { box-sizing: border-box; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: #f0f4f8; margin: 0; padding: 24px 16px; min-height: 100vh;
    }
    .card {
      background: #fff; border-radius: 12px;
      box-shadow: 0 2px 12px rgba(0,0,0,0.10);
      max-width: 480px; margin: 0 auto; padding: 28px 24px 32px;
    }
    h2 { margin: 0 0 4px; font-size: 1.3rem; color: #1a1a2e; }
    #subtitle { color: #555; font-size: 0.88rem; margin: 0 0 16px; }
    .feed { margin-top: 4px; }
    .msg {
      padding: 5px 0; border-bottom: 1px solid #f3f4f6;
      font-size: 0.88rem; line-height: 1.4;
      display: flex; gap: 8px; align-items: flex-start;
    }
    .msg:last-child { border-bottom: none; }
    .dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; margin-top: 4px; }
    .msg.info    .dot { background: #6b7280; }
    .msg.success .dot { background: #16a34a; }
    .msg.error   .dot { background: #dc2626; }
    .msg.warning .dot { background: #d97706; }
    .msg.done    .dot { background: #2563eb; }
    .msg.info    .text { color: #374151; }
    .msg.success .text { color: #15803d; font-weight: 600; }
    .msg.error   .text { color: #b91c1c; font-weight: 600; }
    .msg.warning .text { color: #92400e; }
    .msg.done    .text { color: #1d4ed8; font-weight: 600; }
    .spinner {
      display: inline-block; width: 13px; height: 13px;
      border: 2px solid #d1d5db; border-top-color: #0066cc;
      border-radius: 50%; animation: spin 0.8s linear infinite;
      margin-right: 5px; vertical-align: middle;
    }
    @keyframes spin { to { transform: rotate(360deg); } }
    #plot-wrap { margin-top: 20px; }
    #plot-wrap img {
      width: 100%; border-radius: 8px;
      border: 1px solid #e5e7eb; display: none;
    }
  </style>
</head>
<body>
  <div class="card">
    <h2>&#128274; Credentials received</h2>
    <p id="subtitle"><span class="spinner"></span>Logging in to CERN SSO&hellip;</p>
    <div class="feed" id="feed"></div>
    <div id="plot-wrap">
      <img id="plot-img" src="/plot.png?t=0"
           onload="this.style.display='block'" onerror="this.style.display='none'">
    </div>
  </div>
  <script>
    const feed     = document.getElementById('feed');
    const subtitle = document.getElementById('subtitle');
    const plotImg  = document.getElementById('plot-img');

    function addMsg(kind, text) {
      const row  = document.createElement('div');
      row.className = 'msg ' + kind;
      const dot  = document.createElement('span');
      dot.className = 'dot';
      const span = document.createElement('span');
      span.className = 'text';
      span.textContent = text;
      row.appendChild(dot);
      row.appendChild(span);
      feed.appendChild(row);
      row.scrollIntoView({behavior: 'smooth', block: 'nearest'});
    }

    const src = new EventSource('/events');
    src.onmessage = function(e) {
      const d = JSON.parse(e.data);
      if (d.kind === 'plot_updated') {
        plotImg.src = '/plot.png?t=' + Date.now();
        plotImg.style.display = 'block';
        return;
      }
      addMsg(d.kind, d.text);
      if (d.kind === 'success' && d.text.includes('Login successful')) {
        subtitle.textContent = 'Logged in \u2713 \u2014 scraping reservations\u2026';
      }
      if (d.kind === 'done') {
        subtitle.textContent = '\u2713 Done';
        src.close();
      }
    };
    src.onerror = function() {
      subtitle.textContent = 'Connection closed.';
      src.close();
    };
  </script>
</body>
</html>"""

# ── Error page ─────────────────────────────────────────────────────────────────

_ERROR_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Login failed</title>
  <style>
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: #f0f4f8; display: flex; align-items: center;
      justify-content: center; min-height: 100vh; margin: 0;
    }}
    .card {{
      background: #fff; border-radius: 12px;
      box-shadow: 0 2px 12px rgba(0,0,0,0.10);
      padding: 32px; text-align: center; max-width: 380px;
    }}
    .icon {{ font-size: 2.5rem; margin-bottom: 12px; }}
    h2 {{ margin: 0 0 10px; color: #c0392b; font-size: 1.2rem; }}
    p  {{ margin: 0 0 20px; color: #555; font-size: 0.9rem; line-height: 1.5; }}
    .reason {{
      background: #fef2f2; border-left: 4px solid #ef4444;
      border-radius: 4px; padding: 10px 12px;
      font-size: 0.85rem; color: #555; text-align: left; margin-bottom: 20px;
    }}
    a {{
      display: inline-block; padding: 12px 28px; background: #0066cc;
      color: #fff; font-weight: 600; border-radius: 8px;
      text-decoration: none; font-size: 1rem;
    }}
  </style>
</head>
<body>
  <div class="card">
    <div class="icon">&#10060;</div>
    <h2>Login failed</h2>
    <p>The script could not complete the CERN SSO login.</p>
    <div class="reason">{reason}</div>
    <a href="/">Try again</a>
  </div>
</body>
</html>"""


# ── Helpers ────────────────────────────────────────────────────────────────────

def _get_local_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "localhost"


def _read_creds_file(path: Path) -> tuple[str, str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    if len(lines) < 2:
        raise ValueError(f"Creds file {path} must have at least 2 lines: username, password")
    return lines[0].strip(), lines[1].strip()


def _get_public_ip() -> str | None:
    try:
        with urllib.request.urlopen("https://api.ipify.org", timeout=5) as resp:
            return resp.read().decode().strip()
    except Exception as exc:
        log.warning("Could not fetch public IP: %s", exc)
        return None


# ── LoginServer ────────────────────────────────────────────────────────────────

class LoginServer:
    """
    Temporary Flask server that:
      - Shows a login / 2FA form (with the latest availability plot if saved)
      - After form submission, shows a live status feed via SSE
      - Serves the current plot at /plot.png (refreshable from the status page)
    """

    def __init__(
        self,
        port: int = 5000,
        creds_file: Path | None = None,
        plot_path: Path | None = None,
    ):
        self._port      = port
        self._plot_path = Path(plot_path) if plot_path else None

        self._prefilled_username = ""
        self._prefilled_password = ""
        if creds_file is not None:
            self._prefilled_username, self._prefilled_password = _read_creds_file(
                Path(creds_file)
            )
            log.info(
                "Loaded CERN credentials from %s (username: %s).",
                creds_file, self._prefilled_username,
            )

        self._creds: dict        = {}
        self._creds_ready        = threading.Event()

        self._messages: list[dict] = []   # {'kind': str, 'text': str}
        self._msg_lock             = threading.Lock()
        self._shutdown_flag        = False

        self._wsgi_server  = None
        self._server_thread = None
        self._url           = ""

    # ── Lifecycle ──────────────────────────────────────────────────────────────

    def start(self, on_ready=None) -> str:
        """Build the Flask app, start the server thread, return the public URL."""
        app = Flask(__name__)
        logging.getLogger("werkzeug").setLevel(logging.ERROR)
        srv = self   # capture for route closures

        @app.route("/", methods=["GET", "POST"])
        def form():
            if request.method == "POST":
                srv._creds = {
                    "username": request.form.get("username", "").strip(),
                    "password": request.form.get("password", ""),
                    "totp":     request.form.get("totp", "").strip(),
                }
                srv._creds_ready.set()
                return _STATUS_HTML
            # GET — show the appropriate login form
            if srv._prefilled_username:
                return (
                    _TOTP_ONLY_HTML
                    .replace("{username}", srv._prefilled_username)
                    .replace("{password}", srv._prefilled_password)
                )
            return _FORM_HTML

        @app.route("/plot.png")
        def plot_image():
            if srv._plot_path and srv._plot_path.exists():
                return flask_send_file(
                    str(srv._plot_path.resolve()),
                    mimetype="image/png",
                    max_age=0,
                )
            return "No plot yet", 404

        @app.route("/events")
        def events():
            def generate():
                idx = 0
                while not srv._shutdown_flag:
                    with srv._msg_lock:
                        batch    = srv._messages[idx:]
                        new_idx  = len(srv._messages)
                    for msg in batch:
                        yield f"data: {json.dumps(msg)}\n\n"
                    idx = new_idx
                    if not batch:
                        time.sleep(0.4)
            return Response(
                generate(),
                mimetype="text/event-stream",
                headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
            )

        @app.route("/failed")
        def failed():
            reason = request.args.get("reason", "Unknown error — check the script log.")
            srv._creds_ready.clear()
            srv._creds.clear()
            return _ERROR_HTML.format(reason=reason)

        self._wsgi_server   = make_server("0.0.0.0", self._port, app)
        self._server_thread = threading.Thread(
            target=self._wsgi_server.serve_forever, daemon=True
        )
        self._server_thread.start()

        local_url = f"http://{_get_local_ip()}:{self._port}"
        if self._prefilled_username:
            public_ip  = _get_public_ip()
            self._url  = f"http://{public_ip}:{self._port}" if public_ip else local_url
        else:
            self._url = local_url
        log.info("Login server ready: %s", self._url)

        if on_ready is not None:
            on_ready(self._url)

        return self._url

    # ── Credential handshake ───────────────────────────────────────────────────

    def wait_for_credentials(self) -> dict:
        """Block until the user submits the form. Server stays alive."""
        self._creds_ready.wait()
        self._creds_ready.clear()
        return dict(self._creds)

    def reset(self) -> None:
        """Clear pending credentials so wait_for_credentials() will block again."""
        self._creds.clear()
        self._creds_ready.clear()

    # ── Status broadcasting ────────────────────────────────────────────────────

    def push_status(self, text: str, kind: str = "info") -> None:
        """
        Push a status line to any browser connected to /events.

        kind values: 'info' | 'success' | 'warning' | 'error' | 'done' | 'plot_updated'
        Using kind='done' tells the browser to close the SSE connection.
        Using kind='plot_updated' triggers a plot image refresh (text is ignored).
        """
        with self._msg_lock:
            self._messages.append({"kind": kind, "text": text})

    # ── Shutdown ───────────────────────────────────────────────────────────────

    def shutdown(self) -> None:
        """Stop the server and SSE generator threads."""
        self._shutdown_flag = True
        if self._wsgi_server:
            self._wsgi_server.shutdown()
            if self._server_thread:
                self._server_thread.join(timeout=5)
            self._wsgi_server   = None
            self._server_thread = None
        log.info("Login server shut down.")

    @property
    def url(self) -> str:
        return self._url


# ── Backward-compat one-shot wrapper ──────────────────────────────────────────

def collect_credentials(
    on_ready=None,
    port: int = 5000,
    creds_file: Path | None = None,
    plot_path: Path | None = None,
) -> dict:
    """Start a LoginServer, wait for one credential submission, shut down, return creds."""
    srv = LoginServer(port=port, creds_file=creds_file, plot_path=plot_path)
    srv.start(on_ready=on_ready)
    creds = srv.wait_for_credentials()
    srv.shutdown()
    return creds
