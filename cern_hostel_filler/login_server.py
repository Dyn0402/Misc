"""
login_server.py — multi-tenant Flask server for CERN credential collection and
live status broadcasting, one account per URL slug, all sharing one port.

Each account (identified by a URL-safe `slug`) gets its own page at `/<slug>/`
that is phase-aware:
    "idle"    → status page (nothing pending; shows the latest plot)
    "connect" → Connect form (username prefilled if known; password always blank)
    "2fa"     → TOTP form

Public API:
    LoginServer(port, accounts, primary_slug=None)
        .start()                          → starts server, returns base URL
        .url_for(slug)                    → personal login URL for that account
        .try_get_connect(slug)            → NON-BLOCKING poll; creds dict or None
        .signal_session_ready(slug)       → switch to /2fa and push redirect
        .wait_for_credentials(slug, timeout) → blocks (bounded) for TOTP submit
        .push_status(slug, text, kind)    → push a line to that account's SSE feed
        .push_redirect_home(slug)         → reset to "connect" phase, redirect to /<slug>/
        .set_idle(slug, status_text=None) → switch back to "idle" phase
        .shutdown()                       → stop the server

Each account object passed in `accounts` only needs these attributes (duck-typed,
so no import of cern_hostel_filler.Account is required):
    slug, display_name, cern_username, cern_creds_path, plot_path
"""

import json
import logging
import socket
import threading
import time
import urllib.request
from pathlib import Path

from flask import Flask, request, Response, abort, redirect, send_file as flask_send_file
from werkzeug.serving import make_server

log = logging.getLogger(__name__)

# ── Shared CSS (injected into every page) ──────────────────────────────────────

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
    .status-dot {
      display: inline-block; width: 10px; height: 10px; border-radius: 50%;
      background: #16a34a; margin-right: 6px; vertical-align: middle;
    }
"""

_STATUS_PAGE_CSS = """
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
"""

_ERROR_CSS = """
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: #f0f4f8; display: flex; align-items: center;
      justify-content: center; min-height: 100vh; margin: 0;
    }
    .card {
      background: #fff; border-radius: 12px;
      box-shadow: 0 2px 12px rgba(0,0,0,0.10);
      padding: 32px; text-align: center; max-width: 380px;
    }
    .icon { font-size: 2.5rem; margin-bottom: 12px; }
    h2 { margin: 0 0 10px; color: #c0392b; font-size: 1.2rem; }
    p  { margin: 0 0 20px; color: #555; font-size: 0.9rem; line-height: 1.5; }
    .reason {
      background: #fef2f2; border-left: 4px solid #ef4444;
      border-radius: 4px; padding: 10px 12px;
      font-size: 0.85rem; color: #555; text-align: left; margin-bottom: 20px;
    }
    a {
      display: inline-block; padding: 12px 28px; background: #0066cc;
      color: #fff; font-weight: 600; border-radius: 8px;
      text-decoration: none; font-size: 1rem;
    }
"""


# ── Per-page HTML builders (slug-aware; built per-request, not precomputed) ────

def _plot_img_html(slug: str) -> str:
    return (
        f'<img class="plot-preview" src="/{slug}/plot.png" '
        f'onload="this.style.display=\'block\'" onerror="this.style.display=\'none\'">'
    )


def _page_shell(title: str, css: str, body: str) -> str:
    return (
        f'<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">'
        f'<meta name="viewport" content="width=device-width, initial-scale=1">'
        f'<title>{title}</title><style>{css}</style></head><body>{body}</body></html>'
    )


def _idle_page_html(slug: str, display_name: str, status_text: str) -> str:
    body = f"""
    <div class="card">
      <h2>&#128274; CERN Hostel — {display_name}</h2>
      <p class="subtitle"><span class="status-dot"></span>{status_text}</p>
      <div class="notice">
        Nothing for you to do right now. This page is yours — bookmark it.
        You'll get an email with a fresh link whenever a login is needed.
      </div>
      {_plot_img_html(slug)}
    </div>
    """
    return _page_shell(f"CERN Hostel — {display_name}", _SHARED_CSS, body)


def _connect_page_html(slug: str, display_name: str, prefilled_username: str,
                       has_password: bool) -> str:
    if has_password:
        notice = (
            "Clicking <strong>Connect</strong> will immediately enter your saved "
            "credentials in the browser. You will then be taken to the "
            "<strong>2FA page</strong> to enter your Google Authenticator code."
        )
        form = '<form method="post" action="/{slug}/connect"><button type="submit">Connect &amp; Start Login</button></form>'.format(slug=slug)
    else:
        notice = (
            "Enter your CERN username and password, then tap Connect. They will be "
            "entered in the browser immediately — we don't store your password. "
            "You will then be taken to the <strong>2FA page</strong> for your "
            "Google Authenticator code."
        )
        username_value = f' value="{prefilled_username}"' if prefilled_username else ""
        form = f"""
        <form method="post" action="/{slug}/connect" autocomplete="on">
          <div class="field">
            <label for="username">CERN Username</label>
            <input id="username" name="username" type="text"{username_value}
              autocomplete="username" autocorrect="off" autocapitalize="none"
              spellcheck="false" required autofocus>
          </div>
          <div class="field">
            <label for="password">Password</label>
            <input id="password" name="password" type="password"
              autocomplete="current-password" required>
          </div>
          <button type="submit">Connect &amp; Start Login</button>
        </form>
        """

    body = f"""
    <div class="card">
      <h2>&#128683; Session Expired — {display_name}</h2>
      <p class="subtitle">Your CERN session has expired and must be renewed.</p>
      <div class="notice">{notice}</div>
      {form}
      {_plot_img_html(slug)}
    </div>
    """
    return _page_shell("CERN Hostel — Reconnect", _SHARED_CSS, body)


def _totp_page_html(slug: str, display_name: str) -> str:
    body = f"""
    <div class="card">
      <h2>CERN Hostel — 2FA ({display_name})</h2>
      <p class="subtitle">Credentials accepted. Enter your Google Authenticator code.</p>
      <div class="notice">
        Open your authenticator app <strong>last</strong>, just before tapping
        Submit — TOTP codes expire after 30 seconds.
      </div>
      <form method="post" action="/{slug}/2fa" autocomplete="off">
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
      {_plot_img_html(slug)}
    </div>
    """
    return _page_shell("CERN 2FA", _SHARED_CSS, body)


def _status_page_html(slug: str, display_name: str) -> str:
    body = f"""
    <div class="card">
      <h2>&#128274; CERN Hostel — {display_name}</h2>
      <p id="subtitle"><span class="spinner"></span>Please wait&hellip;</p>
      <div class="feed" id="feed"></div>
      <div id="plot-wrap">
        <img id="plot-img" src="/{slug}/plot.png?t=0"
             onload="this.style.display='block'" onerror="this.style.display='none'">
      </div>
    </div>
    <script>
      const feed     = document.getElementById('feed');
      const subtitle = document.getElementById('subtitle');
      const plotImg  = document.getElementById('plot-img');

      function addMsg(kind, text) {{
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
        row.scrollIntoView({{behavior: 'smooth', block: 'nearest'}});
      }}

      const src = new EventSource('/{slug}/events');
      src.onmessage = function(e) {{
        const d = JSON.parse(e.data);
        if (d.kind === 'plot_updated') {{
          plotImg.src = '/{slug}/plot.png?t=' + Date.now();
          plotImg.style.display = 'block';
          return;
        }}
        if (d.kind === 'redirect') {{
          src.close();
          setTimeout(() => {{ window.location = d.text || '/{slug}/'; }}, 1500);
          return;
        }}
        addMsg(d.kind, d.text);
        if (d.kind === 'success' && d.text.includes('Login successful')) {{
          subtitle.textContent = 'Logged in ✓ — scraping reservations…';
        }}
        if (d.kind === 'done') {{
          subtitle.textContent = '✓ Done';
          src.close();
        }}
      }};
      src.onerror = function() {{
        subtitle.textContent = 'Connection closed.';
        src.close();
      }};
    </script>
    """
    return _page_shell("CERN Hostel — Status", _STATUS_PAGE_CSS, body)


def _error_page_html(slug: str, reason: str) -> str:
    body = f"""
    <div class="card">
      <div class="icon">&#10060;</div>
      <h2>Login failed</h2>
      <p>The script could not complete the CERN SSO login.</p>
      <div class="reason">{reason}</div>
      <a href="/{slug}/">Try again</a>
    </div>
    """
    return _page_shell("Login failed", _ERROR_CSS, body)


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


def _get_public_ip() -> str | None:
    try:
        with urllib.request.urlopen("https://api.ipify.org", timeout=5) as resp:
            return resp.read().decode().strip()
    except Exception as exc:
        log.warning("Could not fetch public IP: %s", exc)
        return None


def _read_creds_file(path: Path) -> tuple[str, str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    if len(lines) < 2:
        raise ValueError(f"Creds file {path} must have at least 2 lines: username, password")
    return lines[0].strip(), lines[1].strip()


# ── Per-account state ──────────────────────────────────────────────────────────

class _AccountLogin:
    """All mutable state for one account's login/status page."""

    def __init__(self, slug, display_name, prefilled_username, prefilled_password, plot_path):
        self.slug             = slug
        self.display_name     = display_name
        self.prefilled_username = prefilled_username
        self.prefilled_password = prefilled_password
        self.plot_path        = Path(plot_path) if plot_path else None

        self.phase        = "idle"   # "idle" | "connect" | "2fa"
        self.status_text  = "System running normally."

        self.connect_creds: dict = {}
        self.creds: dict         = {}
        self.creds_ready         = threading.Event()
        self.connect_event       = threading.Event()

        self.messages: list[dict] = []
        self.msg_lock             = threading.Lock()

    def clear_messages(self):
        with self.msg_lock:
            self.messages.clear()

    def push(self, text: str, kind: str = "info"):
        with self.msg_lock:
            self.messages.append({"kind": kind, "text": text})


# ── LoginServer ────────────────────────────────────────────────────────────────

class LoginServer:
    """
    One Flask app, one port, many accounts — each at its own `/<slug>/` URL.

    Flow per account:
        GET  /<slug>/        → idle status / Connect form / TOTP form (phase-aware)
        POST /<slug>/connect → registers connect creds, signals try_get_connect()
        (scheduler opens playwright, enters username/password — step 1)
        (scheduler calls signal_session_ready(slug) once OTP page is reached)
        GET  /<slug>/2fa     → TOTP-only form
        POST /<slug>/2fa     → registers TOTP, signals wait_for_credentials()
        (scheduler enters TOTP — step 2, pushes status via push_status())
    """

    def __init__(self, port: int, accounts: list, primary_slug: str | None = None):
        self._port         = port
        self._primary_slug = primary_slug or (accounts[0].slug if accounts else None)

        self._accounts: dict[str, _AccountLogin] = {}
        for acc in accounts:
            prefilled_user = ""
            prefilled_pass = ""
            has_password   = False
            if getattr(acc, "cern_creds_path", None) is not None and Path(acc.cern_creds_path).exists():
                prefilled_user, prefilled_pass = _read_creds_file(Path(acc.cern_creds_path))
                has_password = True
            elif getattr(acc, "cern_username", None):
                prefilled_user = acc.cern_username

            self._accounts[acc.slug] = _AccountLogin(
                slug=acc.slug,
                display_name=acc.display_name,
                prefilled_username=prefilled_user,
                prefilled_password=prefilled_pass if has_password else "",
                plot_path=getattr(acc, "plot_path", None),
            )
            # Stash whether this account has a full saved password (changes which
            # connect-page variant is shown) without polluting _AccountLogin's
            # public surface.
            self._accounts[acc.slug]._has_password = has_password

            log.info(
                "Registered login page for %-10s → /%s/  (%s)",
                acc.display_name, acc.slug,
                "saved credentials" if has_password else
                (f"username prefilled: {prefilled_user}" if prefilled_user else "full manual login"),
            )

        self._shutdown_flag  = False
        self._wsgi_server    = None
        self._server_thread  = None
        self._url            = ""

    # ── Lifecycle ──────────────────────────────────────────────────────────────

    def _account(self, slug: str) -> _AccountLogin:
        acc = self._accounts.get(slug)
        if acc is None:
            abort(404)
        return acc

    def start(self) -> str:
        """Build the Flask app, start the server thread, return the base URL."""
        app = Flask(__name__)
        logging.getLogger("werkzeug").setLevel(logging.ERROR)
        srv = self

        @app.route("/", methods=["GET"])
        def root():
            if srv._primary_slug:
                return redirect(f"/{srv._primary_slug}/")
            return "No accounts configured", 404

        @app.route("/<slug>/", methods=["GET"])
        def account_page(slug):
            acc = srv._account(slug)
            if acc.phase == "2fa":
                return _totp_page_html(slug, acc.display_name)
            if acc.phase == "connect":
                return _connect_page_html(
                    slug, acc.display_name, acc.prefilled_username, acc._has_password
                )
            return _idle_page_html(slug, acc.display_name, acc.status_text)

        @app.route("/<slug>/connect", methods=["POST"])
        def connect(slug):
            acc = srv._account(slug)
            if acc.phase != "connect":
                # Stale page / accidental click — nothing pending for this account.
                return redirect(f"/{slug}/")
            acc.clear_messages()
            acc.push("Starting browser session — entering credentials…")
            acc.connect_creds = {
                "username": request.form.get("username", "").strip() or acc.prefilled_username,
                "password": request.form.get("password", "") or acc.prefilled_password,
            }
            acc.connect_event.set()
            return _status_page_html(slug, acc.display_name)

        @app.route("/<slug>/2fa", methods=["GET"])
        def totp_form(slug):
            acc = srv._account(slug)
            if acc.phase != "2fa":
                return redirect(f"/{slug}/")
            return _totp_page_html(slug, acc.display_name)

        @app.route("/<slug>/2fa", methods=["POST"])
        def totp_submit(slug):
            acc = srv._account(slug)
            if acc.phase != "2fa":
                return redirect(f"/{slug}/")
            acc.clear_messages()
            acc.push("2FA code received — completing login…")
            acc.creds = {"totp": request.form.get("totp", "").strip()}
            acc.creds_ready.set()
            return _status_page_html(slug, acc.display_name)

        @app.route("/<slug>/plot.png")
        def plot_image(slug):
            acc = srv._account(slug)
            if acc.plot_path and acc.plot_path.exists():
                return flask_send_file(
                    str(acc.plot_path.resolve()), mimetype="image/png", max_age=0,
                )
            return "No plot yet", 404

        @app.route("/<slug>/events")
        def events(slug):
            acc = srv._account(slug)
            start_idx = len(acc.messages)

            def generate():
                idx = start_idx
                while not srv._shutdown_flag:
                    with acc.msg_lock:
                        batch   = acc.messages[idx:]
                        new_idx = len(acc.messages)
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

        @app.route("/<slug>/failed")
        def failed(slug):
            acc = srv._account(slug)
            reason = request.args.get("reason", "Unknown error — check the script log.")
            acc.creds_ready.clear()
            acc.creds.clear()
            return _error_page_html(slug, reason)

        self._wsgi_server   = make_server("0.0.0.0", self._port, app, threaded=True)
        self._server_thread = threading.Thread(
            target=self._wsgi_server.serve_forever, daemon=True
        )
        self._server_thread.start()

        local_url   = f"http://{_get_local_ip()}:{self._port}"
        public_ip   = _get_public_ip()
        self._url   = f"http://{public_ip}:{self._port}" if public_ip else local_url
        log.info("Login server ready: %s  (accounts: %s)", self._url, ", ".join(self._accounts))

        return self._url

    # ── Per-account URL ────────────────────────────────────────────────────────

    def url_for(self, slug: str) -> str:
        return f"{self._url}/{slug}/"

    # ── Connect handshake ──────────────────────────────────────────────────────

    def begin_login(self, slug: str) -> None:
        """Switch an account's page to the Connect form (call when its session expires)."""
        acc = self._account(slug)
        acc.connect_creds.clear()
        acc.creds.clear()
        acc.creds_ready.clear()
        acc.connect_event.clear()
        acc.phase = "connect"

    def try_get_connect(self, slug: str) -> dict | None:
        """
        NON-BLOCKING poll: has the user clicked Connect for this account yet?
        Returns {"username": str, "password": str} if so (and re-arms for next
        time), or None if nothing has happened yet. Never blocks the caller —
        this is what lets other accounts' checks run on schedule while one
        account's user takes their time logging in.
        """
        acc = self._account(slug)
        if not acc.connect_event.is_set():
            return None
        acc.connect_event.clear()
        return dict(acc.connect_creds)

    def signal_session_ready(self, slug: str) -> None:
        """Mark an account as being in the 2FA phase and redirect its page to /2fa."""
        acc = self._account(slug)
        acc.phase = "2fa"
        acc.push("/" + slug + "/2fa", kind="redirect")

    def push_redirect_home(self, slug: str) -> None:
        """Reset an account to the Connect phase and redirect its page to /<slug>/."""
        acc = self._account(slug)
        acc.phase = "connect"
        acc.push(f"/{slug}/", kind="redirect")

    # ── Credential handshake ───────────────────────────────────────────────────

    def wait_for_credentials(self, slug: str, timeout: float | None = None) -> dict | None:
        """
        Block (with a bounded timeout — the TOTP step, ~5 min) until the user
        submits the 2FA form for this account. Returns the credential dict, or
        None on timeout. Automatically re-arms for next time.
        """
        acc = self._account(slug)
        result = acc.creds_ready.wait(timeout=timeout)
        acc.creds_ready.clear()
        if not result:
            return None
        return dict(acc.creds)

    # ── Idle / status ──────────────────────────────────────────────────────────

    def set_idle(self, slug: str, status_text: str | None = None) -> None:
        """Switch an account's page back to its normal idle status view."""
        acc = self._account(slug)
        acc.phase = "idle"
        if status_text is not None:
            acc.status_text = status_text

    def update_idle_status(self, slug: str, status_text: str) -> None:
        acc = self._account(slug)
        acc.status_text = status_text

    # ── Status broadcasting (active login / check-in-progress feed) ────────────

    def push_status(self, slug: str, text: str, kind: str = "info") -> None:
        """
        Push a status line to whatever browser is connected to /<slug>/events.

        kind values: 'info' | 'success' | 'warning' | 'error' | 'done' | 'plot_updated' | 'redirect'
        """
        self._account(slug).push(text, kind)

    # ── Shutdown ───────────────────────────────────────────────────────────────

    def shutdown(self) -> None:
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
