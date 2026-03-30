"""
login_server.py — temporary Flask server that collects CERN SSO credentials
from a mobile-friendly web page and returns them to the calling script.

Usage:
    creds = collect_credentials(
        on_ready=lambda url: print(f"Open {url}"),
        creds_file=Path("~/Desktop/creds/cern.txt"),  # username on line 1, password on line 2
    )
    # creds == {'username': '...', 'password': '...', 'totp': '...'}
"""

import logging
import re
import socket
import subprocess
import threading
import time
from pathlib import Path

from flask import Flask, request
from werkzeug.serving import make_server

log = logging.getLogger(__name__)

# ── HTML templates ─────────────────────────────────────────────────────────────

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
"""

# Full form (username + password + TOTP) — shown when no creds file is configured.
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
  </div>
</body>
</html>""".format(css=_SHARED_CSS)

# TOTP-only form — shown when username/password are pre-loaded from a creds file.
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
  </div>
</body>
</html>""".format(css=_SHARED_CSS)

_SUCCESS_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Logging in…</title>
  <style>
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: #f0f4f8;
      display: flex;
      align-items: center;
      justify-content: center;
      min-height: 100vh;
      margin: 0;
    }
    .card {
      background: #fff;
      border-radius: 12px;
      box-shadow: 0 2px 12px rgba(0,0,0,0.10);
      padding: 40px 32px;
      text-align: center;
      max-width: 340px;
    }
    .icon { font-size: 2.5rem; margin-bottom: 12px; }
    h2 { margin: 0 0 8px; color: #1a1a2e; font-size: 1.3rem; }
    p  { margin: 0; color: #555; font-size: 0.95rem; line-height: 1.5; }
  </style>
</head>
<body>
  <div class="card">
    <div class="icon">&#128274;</div>
    <h2>Credentials received</h2>
    <p>The script is now logging in to CERN SSO.<br>You can close this page.</p>
  </div>
</body>
</html>"""

_ERROR_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Login failed</title>
  <style>
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: #f0f4f8;
      display: flex;
      align-items: center;
      justify-content: center;
      min-height: 100vh;
      margin: 0;
    }}
    .card {{
      background: #fff;
      border-radius: 12px;
      box-shadow: 0 2px 12px rgba(0,0,0,0.10);
      padding: 32px;
      text-align: center;
      max-width: 380px;
    }}
    .icon {{ font-size: 2.5rem; margin-bottom: 12px; }}
    h2 {{ margin: 0 0 10px; color: #c0392b; font-size: 1.2rem; }}
    p  {{ margin: 0 0 20px; color: #555; font-size: 0.9rem; line-height: 1.5; }}
    .reason {{
      background: #fef2f2;
      border-left: 4px solid #ef4444;
      border-radius: 4px;
      padding: 10px 12px;
      font-size: 0.85rem;
      color: #555;
      text-align: left;
      margin-bottom: 20px;
    }}
    a {{
      display: inline-block;
      padding: 12px 28px;
      background: #0066cc;
      color: #fff;
      font-weight: 600;
      border-radius: 8px;
      text-decoration: none;
      font-size: 1rem;
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
    """Return the machine's primary LAN IP (not 127.0.0.1)."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "localhost"


def _read_creds_file(path: Path) -> tuple[str, str]:
    """Read username (line 1) and password (line 2) from a plain-text file."""
    lines = path.read_text(encoding="utf-8").splitlines()
    if len(lines) < 2:
        raise ValueError(f"Creds file {path} must have at least 2 lines: username, password")
    return lines[0].strip(), lines[1].strip()


def _start_ssh_tunnel(port: int) -> str | None:
    """
    Open a reverse SSH tunnel via serveo.net and return the public HTTPS URL.
    Returns None if the tunnel cannot be established within 10 seconds.
    """
    try:
        proc = subprocess.Popen(
            ["ssh", "-o", "StrictHostKeyChecking=no",
             "-o", "ServerAliveInterval=30",
             "-R", f"80:localhost:{port}",
             "serveo.net"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        deadline = time.monotonic() + 10
        for line in proc.stdout:  # type: ignore[union-attr]
            if time.monotonic() > deadline:
                break
            m = re.search(r"https?://\S+\.serveo\.net", line)
            if m:
                log.info("SSH tunnel established: %s", m.group())
                return m.group()
        log.warning("Could not parse serveo.net tunnel URL within 10 s; falling back to LAN IP.")
        return None
    except FileNotFoundError:
        log.warning("ssh not found; cannot open external tunnel.")
        return None
    except Exception as exc:
        log.warning("SSH tunnel failed: %s", exc)
        return None


# ── Public API ─────────────────────────────────────────────────────────────────

def collect_credentials(
    on_ready=None,
    port: int = 5000,
    creds_file: Path | None = None,
) -> dict:
    """
    Start a temporary Flask server on *port*, then block until the user submits
    the login form.  Shuts the server down cleanly afterwards.

    Parameters
    ----------
    on_ready : callable(url: str) | None
        Called once the server is listening, with the public URL the user
        should open.
    port : int
        TCP port to listen on (default 5000).
    creds_file : Path | None
        Path to a plain-text file containing the CERN username on line 1 and
        the password on line 2.  When provided, only the TOTP field is shown
        and the server also tries to open an external SSH tunnel via
        serveo.net so it is reachable from outside the local network.

    Returns
    -------
    dict with keys 'username', 'password', 'totp'
    """
    app = Flask(__name__)
    logging.getLogger("werkzeug").setLevel(logging.ERROR)

    # Pre-load username/password if a creds file was given.
    prefilled_username: str = ""
    prefilled_password: str = ""
    if creds_file is not None:
        prefilled_username, prefilled_password = _read_creds_file(Path(creds_file))
        log.info("Loaded CERN credentials from %s (username: %s).", creds_file, prefilled_username)

    creds: dict = {}
    _done = threading.Event()

    @app.route("/", methods=["GET", "POST"])
    def form():
        if request.method == "POST":
            creds["username"] = request.form.get("username", "").strip()
            creds["password"] = request.form.get("password", "")
            creds["totp"]     = request.form.get("totp", "").strip()
            _done.set()
            return _SUCCESS_HTML
        if prefilled_username:
            # Render TOTP-only page with hidden username/password fields.
            return _TOTP_ONLY_HTML.replace(
                "{username}", prefilled_username
            ).replace(
                "{password}", prefilled_password
            )
        return _FORM_HTML

    @app.route("/failed")
    def failed():
        reason = request.args.get("reason", "Unknown error — check the script log.")
        _done.clear()
        creds.clear()
        return _ERROR_HTML.format(reason=reason)

    wsgi_server = make_server("0.0.0.0", port, app)
    server_thread = threading.Thread(target=wsgi_server.serve_forever, daemon=True)
    server_thread.start()

    # Determine the URL to advertise.
    local_url = f"http://{_get_local_ip()}:{port}"
    if creds_file is not None:
        public_url = _start_ssh_tunnel(port)
        url = public_url or local_url
    else:
        url = local_url
    log.info("Login server ready: %s", url)

    if on_ready is not None:
        on_ready(url)

    while True:
        _done.wait()
        if creds.get("username") and creds.get("password") and creds.get("totp"):
            break
        _done.clear()

    wsgi_server.shutdown()
    server_thread.join(timeout=5)
    log.info("Login server shut down.")
    return creds
