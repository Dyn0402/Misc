#!/usr/bin/env python3
"""
Palaiseau Appointment Checker
==============================
Polls the RDV-préfecture slot pages for Palaiseau (demarches 2246 and 2282)
and alerts you when an appointment slot becomes available.

Usage:
    python palaiseau_appointment_checker.py [--interval MINUTES]

First run: a browser window opens. The site redirects to a CAPTCHA page —
solve it manually, then press Enter in the terminal. While waiting for the
CAPTCHA to be solved a gentle tone plays every 5 minutes as a reminder.
When slots become available a louder tone repeats until the next check finds
no slots. Email is only sent for available slots.

Dependencies:
    pip install playwright playwright-stealth
    playwright install chrome
"""

import argparse
import logging
import re
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from playwright_stealth import Stealth
from gmail_notifier import GmailNotifier

# ── User configuration ────────────────────────────────────────────────────────

TARGET_URLS = [
    "https://www.rdv-prefecture.interieur.gouv.fr/rdvpref/reservation/demarche/2246/creneau/",
    "https://www.rdv-prefecture.interieur.gouv.fr/rdvpref/reservation/demarche/2282/creneau/",
]

NOTIFY_EMAIL    = "dyn040294@gmail.com"
GMAIL_CRED_PATH = Path.home() / "Desktop/creds/gmail_cred.txt"

CHECK_INTERVAL_MINUTES = 5

LOG_FILE = Path("palaiseau_appointment_checker.log")

# Seconds between gentle reminder tones while CAPTCHA is pending
CAPTCHA_REMINDER_INTERVAL = 300   # 5 minutes

# Seconds between alarm tones while slots are available
ALARM_INTERVAL = 30

# ── End of configuration ──────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
    ],
)
log = logging.getLogger(__name__)

STEALTH = Stealth(navigator_platform_override="Linux x86_64")

NO_SLOTS_TEXT        = "Aucun créneau disponible"
SLOTS_AVAILABLE_TEXT = "Choisissez votre créneau"
CAPTCHA_URL_PAT = re.compile(r"/cgu/")
SLOTS_URL_PAT   = re.compile(r"/creneau/")

# Captures: "Dernière mise en ligne de rendez-vous : le 04/05/2026 à 11:58
#            pour des créneaux de la semaine du 18/05/2026"
LAST_UPDATE_PAT = re.compile(
    r"Dernière mise en ligne.*?(?=\n\n|\Z)", re.IGNORECASE | re.DOTALL
)


# ── Sound ─────────────────────────────────────────────────────────────────────

_SOUND_GENTLE = "/usr/share/sounds/freedesktop/stereo/bell.oga"
_SOUND_ALERT  = "/usr/share/sounds/freedesktop/stereo/complete.oga"


def _play(sound_path: str):
    try:
        subprocess.run(
            ["paplay", sound_path],
            timeout=5, check=False,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
    except Exception:
        print("\a", end="", flush=True)   # terminal bell fallback


def _make_repeating_thread(sound_path: str, interval: int) -> tuple[threading.Thread, threading.Event]:
    """Return (thread, stop_event). Thread plays sound immediately then every interval seconds."""
    stop = threading.Event()

    def _loop():
        _play(sound_path)
        while not stop.wait(timeout=interval):
            _play(sound_path)

    t = threading.Thread(target=_loop, daemon=True)
    return t, stop


# ── Page helpers ──────────────────────────────────────────────────────────────

def _make_page(ctx):
    page = ctx.new_page()
    STEALTH.apply_stealth_sync(page)
    return page


def _on_slots_page(page) -> bool:
    return SLOTS_URL_PAT.search(page.url) is not None


def _on_captcha_page(page) -> bool:
    return CAPTCHA_URL_PAT.search(page.url) is not None


def _get_body(page) -> str:
    try:
        return page.inner_text("body")
    except Exception:
        return ""


def _extract_last_update(body: str) -> str:
    m = LAST_UPDATE_PAT.search(body)
    if not m:
        return ""
    return " ".join(m.group(0).split())


def _slots_available(body: str) -> bool:
    return SLOTS_AVAILABLE_TEXT in body


# ── CAPTCHA handling ──────────────────────────────────────────────────────────

def _wait_for_captcha_solve(page, url: str) -> bool:
    """
    Navigate to url and wait (automatically) until the CAPTCHA is solved
    and the browser lands on creneau/. Plays a gentle reminder tone every
    CAPTCHA_REMINDER_INTERVAL seconds while waiting.
    """
    log.info("[%s] Navigating to slot page…", url)
    page.goto(url, wait_until="domcontentloaded")
    time.sleep(1)

    if _on_slots_page(page):
        log.info("[%s] Already on slots page — no CAPTCHA needed.", url)
        return True

    if _on_captcha_page(page):
        log.info("[%s] CAPTCHA detected — solve it in the browser window.", url)
    else:
        log.warning("[%s] Unexpected landing page: %s", url, page.url)

    reminder_thread, reminder_stop = _make_repeating_thread(_SOUND_GENTLE, CAPTCHA_REMINDER_INTERVAL)
    reminder_thread.start()

    # Poll until the browser reaches creneau/
    while not _on_slots_page(page):
        try:
            page.wait_for_url("**/creneau/**", timeout=60_000)
        except PlaywrightTimeoutError:
            log.info("[%s] Still waiting for CAPTCHA to be solved…", url)

    reminder_stop.set()
    log.info("[%s] CAPTCHA solved — now on slots page.", url)
    return True


# ── Single check ──────────────────────────────────────────────────────────────

def _check_slots(page, url: str) -> tuple[bool, str] | None:
    """
    Navigate to url and check for available slots.

    Returns:
        (available: bool, body: str) — normal result
        None                         — session expired / CAPTCHA required again
    """
    page.goto(url, wait_until="domcontentloaded")
    time.sleep(1)

    if _on_captcha_page(page):
        log.warning("Session expired — CAPTCHA page appeared.")
        return None

    if not _on_slots_page(page):
        log.warning("Unexpected page after reload: %s", page.url)
        return None

    body      = _get_body(page)
    available = _slots_available(body)
    return available, body


# ── Email notification ────────────────────────────────────────────────────────

def _send_email(subject: str, body: str):
    if not GMAIL_CRED_PATH.exists():
        log.info("No Gmail credentials at %s — skipping email.", GMAIL_CRED_PATH)
        return
    try:
        notifier = GmailNotifier(str(GMAIL_CRED_PATH))
        notifier.send_email(NOTIFY_EMAIL, subject, body)
        log.info("Email sent to %s: %s", NOTIFY_EMAIL, subject)
    except Exception as exc:
        log.error("Failed to send email: %s", exc)


def _notify_slots_available(target_url: str, last_update: str):
    subject = "[ACTION REQUIRED] Palaiseau appointment slot available!"
    body = (
        f"An appointment slot has become available:\n\n"
        f"  Book now: {target_url}\n\n"
        f"  Detected at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"  {last_update}\n"
    )
    _send_email(subject, body)


# ── Per-URL browser loop ──────────────────────────────────────────────────────

def _run_single_url(url: str, interval_minutes: int):
    """Owns one browser instance and polls one URL indefinitely."""
    last_notified    = False
    last_update_seen = ""
    session_start: datetime | None = None

    alarm_thread: threading.Thread | None = None
    alarm_stop:   threading.Event  | None = None

    def _start_alarm():
        nonlocal alarm_thread, alarm_stop
        if alarm_thread and alarm_thread.is_alive():
            return
        t, s = _make_repeating_thread(_SOUND_ALERT, ALARM_INTERVAL)
        alarm_thread, alarm_stop = t, s
        t.start()

    def _stop_alarm():
        nonlocal alarm_thread, alarm_stop
        if alarm_stop:
            alarm_stop.set()
        alarm_thread = None
        alarm_stop   = None

    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel="chrome", headless=False)
        ctx = browser.new_context(
            viewport={"width": 1280, "height": 900},
            extra_http_headers={"Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7"},
        )
        page = _make_page(ctx)

        _wait_for_captcha_solve(page, url)
        session_start = datetime.now()
        log.info("[%s] Session started at %s", url, session_start.strftime("%Y-%m-%d %H:%M:%S"))

        while True:
            result = _check_slots(page, url)

            if result is None:
                _stop_alarm()
                if session_start:
                    duration = datetime.now() - session_start
                    mins = int(duration.total_seconds() // 60)
                    secs = int(duration.total_seconds() % 60)
                    log.info("[%s] Session expired after %dm %ds", url, mins, secs)
                    session_start = None
                _wait_for_captcha_solve(page, url)
                session_start = datetime.now()
                log.info("[%s] New session at %s", url, session_start.strftime("%Y-%m-%d %H:%M:%S"))
                last_notified = False
                continue

            available, body = result
            last_update = _extract_last_update(body)

            if last_update and last_update != last_update_seen:
                log.info("[%s] Slot data updated: %s", url, last_update)
                last_update_seen = last_update

            if available:
                log.info("[%s] *** SLOTS AVAILABLE ***  %s", url, last_update)
                _start_alarm()
                if not last_notified:
                    _notify_slots_available(url, last_update)
                    last_notified = True
                else:
                    log.info("[%s] (alarm already sounding — skipping repeat email)", url)
            else:
                log.info("[%s] No slots.  %s", url, last_update or "(no update timestamp found)")
                _stop_alarm()
                last_notified = False

            log.info("[%s] Next check in %d minute(s).", url, interval_minutes)
            time.sleep(interval_minutes * 60)

        browser.close()


# ── Main entry ────────────────────────────────────────────────────────────────

def run(interval_minutes: int):
    log.info("=" * 60)
    log.info("Palaiseau Appointment Checker  |  interval=%dm  |  %d URL(s)", interval_minutes, len(TARGET_URLS))
    log.info("=" * 60)

    threads = [
        threading.Thread(
            target=_run_single_url,
            args=(url, interval_minutes),
            daemon=True,
            name=f"checker-{i}",
        )
        for i, url in enumerate(TARGET_URLS)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()


def main():
    parser = argparse.ArgumentParser(description="Poll Palaiseau prefecture for appointment slots.")
    parser.add_argument(
        "--interval", type=int, default=CHECK_INTERVAL_MINUTES, metavar="MINUTES",
        help=f"Minutes between checks (default: {CHECK_INTERVAL_MINUTES})",
    )
    args = parser.parse_args()
    try:
        run(interval_minutes=args.interval)
    except KeyboardInterrupt:
        log.info("Stopped by user.")


if __name__ == "__main__":
    main()
