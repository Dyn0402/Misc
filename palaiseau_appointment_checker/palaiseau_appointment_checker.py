#!/usr/bin/env python3
"""
Palaiseau Appointment Checker
==============================
Polls the RDV-préfecture slot page for Palaiseau (demarche 2246) and alerts
you when an appointment slot becomes available.

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

TARGET_URL = "https://www.rdv-prefecture.interieur.gouv.fr/rdvpref/reservation/demarche/2246/creneau/"

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

NO_SLOTS_TEXT   = "Aucun créneau disponible"
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
    return NO_SLOTS_TEXT not in body


# ── CAPTCHA handling ──────────────────────────────────────────────────────────

def _wait_for_captcha_solve(page) -> bool:
    """
    Navigate to TARGET_URL and pause until the user solves the CAPTCHA.
    A gentle reminder tone plays every CAPTCHA_REMINDER_INTERVAL seconds.
    Returns True when we land on creneau/.
    """
    log.info("Navigating to %s", TARGET_URL)
    page.goto(TARGET_URL, wait_until="domcontentloaded")
    time.sleep(1)

    if _on_slots_page(page):
        log.info("Already on slots page — no CAPTCHA needed.")
        return True

    if _on_captcha_page(page):
        log.info("CAPTCHA page detected (%s).", page.url)
    else:
        log.warning("Unexpected landing page: %s", page.url)

    print("\n" + "=" * 60)
    print("  Solve the CAPTCHA in the browser window.")
    print("  Once you see 'Aucun créneau disponible' or actual slots,")
    print("  press Enter here.")
    print("=" * 60)

    # Start gentle reminder tones while we wait
    reminder_thread, reminder_stop = _make_repeating_thread(_SOUND_GENTLE, CAPTCHA_REMINDER_INTERVAL)
    reminder_thread.start()

    input("\n  [Press Enter when ready] ")
    reminder_stop.set()

    # Wait up to 10 s for the redirect to creneau/ to settle
    try:
        page.wait_for_url("**/creneau/**", timeout=10_000)
    except PlaywrightTimeoutError:
        log.warning("Still not on creneau/ after 10 s — current URL: %s", page.url)

    if _on_slots_page(page):
        log.info("CAPTCHA solved — now on slots page.")
        return True

    log.error("Did not reach slots page after CAPTCHA. URL: %s", page.url)
    return False


# ── Single check ──────────────────────────────────────────────────────────────

def _check_slots(page) -> tuple[bool, str] | None:
    """
    Reload the page and check for available slots.

    Returns:
        (available: bool, body: str) — normal result
        None                         — session expired / CAPTCHA required again
    """
    page.reload(wait_until="domcontentloaded")
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


def _notify_slots_available(page_url: str, last_update: str):
    subject = "[ACTION REQUIRED] Palaiseau appointment slot available!"
    body = (
        "An appointment slot has become available for:\n"
        "  Remise de titre — Palaiseau Hall A, Guichet 12\n\n"
        f"  Book now: {page_url}\n\n"
        f"  Detected at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"  {last_update}\n"
    )
    _send_email(subject, body)


# ── Main loop ─────────────────────────────────────────────────────────────────

def run(interval_minutes: int):
    log.info("=" * 60)
    log.info("Palaiseau Appointment Checker  |  interval=%dm", interval_minutes)
    log.info("=" * 60)

    last_notified_available = False
    last_update_seen        = ""
    session_start: datetime | None = None

    # Alarm state (slots available)
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

        # Initial navigation + CAPTCHA solve
        if not _wait_for_captcha_solve(page):
            log.error("Could not reach slots page — exiting.")
            browser.close()
            return
        session_start = datetime.now()
        log.info("Session started at %s", session_start.strftime("%Y-%m-%d %H:%M:%S"))

        # Main polling loop
        while True:
            result = _check_slots(page)

            if result is None:
                # Session expired
                _stop_alarm()
                if session_start:
                    duration = datetime.now() - session_start
                    mins = int(duration.total_seconds() // 60)
                    secs = int(duration.total_seconds() % 60)
                    log.info(
                        "Session expired after %dm %ds (started %s)",
                        mins, secs, session_start.strftime("%H:%M:%S"),
                    )
                    session_start = None

                log.info("Waiting for CAPTCHA to be solved again…")
                if not _wait_for_captcha_solve(page):
                    log.error("Could not recover — exiting.")
                    break
                session_start = datetime.now()
                log.info("New session started at %s", session_start.strftime("%Y-%m-%d %H:%M:%S"))
                last_notified_available = False
                continue

            available, body = result
            last_update = _extract_last_update(body)

            # Log when the site's own "last updated" timestamp changes
            if last_update and last_update != last_update_seen:
                log.info("Slot data updated: %s", last_update)
                last_update_seen = last_update

            if available:
                log.info("*** SLOTS AVAILABLE ***  %s", last_update)
                _start_alarm()
                if not last_notified_available:
                    _notify_slots_available(page.url, last_update)
                    last_notified_available = True
                else:
                    log.info("(alarm already sounding — skipping repeat email)")
            else:
                log.info(
                    "No slots.  %s",
                    last_update or "(no update timestamp found)",
                )
                _stop_alarm()
                last_notified_available = False

            log.info("Next check in %d minute(s).", interval_minutes)
            time.sleep(interval_minutes * 60)

        browser.close()


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
