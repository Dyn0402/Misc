#!/usr/bin/env python3
"""
Palaiseau Appointment Checker
==============================
Polls the RDV-préfecture slot page for Palaiseau (demarche 2246) and emails
you when an appointment slot becomes available.

Usage:
    python palaiseau_appointment_checker.py [--interval MINUTES]

First run: a browser window opens. The site redirects to a CAPTCHA page —
solve it manually, then press Enter in the terminal. The session cookie is
kept alive in memory, so the CAPTCHA is only needed again when it expires.

Dependencies:
    pip install playwright playwright-stealth
    playwright install chrome   (or use system Chrome)
"""

import argparse
import logging
import re
import sys
import time
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from playwright_stealth import Stealth

# ── User configuration ────────────────────────────────────────────────────────

TARGET_URL = "https://www.rdv-prefecture.interieur.gouv.fr/rdvpref/reservation/demarche/2246/creneau/"

NOTIFY_EMAIL    = "dyn040294@gmail.com"
GMAIL_CRED_PATH = Path.home() / "Desktop/creds/gmail_cred.txt"

CHECK_INTERVAL_MINUTES = 5

LOG_FILE = Path("palaiseau_appointment_checker.log")

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
LAST_UPDATE_PAT = re.compile(r"Dernière mise en ligne[^.]*\.?", re.IGNORECASE)


# ── Browser helpers ───────────────────────────────────────────────────────────

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
    # Collapse internal newlines / extra whitespace into a single line
    return " ".join(m.group(0).split())


def _slots_available(body: str) -> bool:
    return NO_SLOTS_TEXT not in body


# ── CAPTCHA handling ──────────────────────────────────────────────────────────

def _wait_for_captcha_solve(page) -> bool:
    """
    Navigate to TARGET_URL, handle the CAPTCHA redirect, and pause until the
    user solves the puzzle manually.  Returns True when we land on creneau/.
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
    input("\n  [Press Enter when ready] ")

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

def _check_slots(page) -> bool | None:
    """
    Reload the page and check for available slots.

    Returns:
        True   — slots available (send notification)
        False  — no slots
        None   — session expired / CAPTCHA required again
    """
    page.reload(wait_until="domcontentloaded")
    time.sleep(1)

    if _on_captcha_page(page):
        log.warning("Session expired — CAPTCHA page appeared.")
        return None

    if not _on_slots_page(page):
        log.warning("Unexpected page after reload: %s", page.url)
        return None

    body = _get_body(page)
    last_update = _extract_last_update(body)
    available   = _slots_available(body)

    log.info(
        "Check complete — slots_available=%s  url=%s  %s",
        available, page.url, last_update or "(no update timestamp found)",
    )
    return available


# ── Email notification ────────────────────────────────────────────────────────

def _send_email(subject: str, body: str):
    if not GMAIL_CRED_PATH.exists():
        log.info("No Gmail credentials at %s — skipping email.", GMAIL_CRED_PATH)
        return
    sys.path.insert(0, str(Path(__file__).parent.parent / "cern_hostel_filler"))
    try:
        from gmail_notifier import GmailNotifier
        notifier = GmailNotifier(str(GMAIL_CRED_PATH))
        notifier.send_email(NOTIFY_EMAIL, subject, body)
        log.info("Email sent to %s: %s", NOTIFY_EMAIL, subject)
    except Exception as exc:
        log.error("Failed to send email: %s", exc)


def _notify_slots_available(page_url: str):
    subject = "[ACTION REQUIRED] Palaiseau appointment slot available!"
    body = (
        "An appointment slot has become available for:\n"
        "  Remise de titre — Palaiseau Hall A, Guichet 12\n\n"
        f"  Book now: {TARGET_URL}\n\n"
        f"  Detected at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"  Page URL: {page_url}\n"
    )
    _send_email(subject, body)


def _notify_session_expired():
    subject = "[ACTION REQUIRED] Palaiseau checker: CAPTCHA required"
    body = (
        "The Palaiseau appointment checker session has expired.\n"
        "Please restart the script and solve the CAPTCHA again.\n\n"
        f"  Detected at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    )
    _send_email(subject, body)


# ── Main loop ─────────────────────────────────────────────────────────────────

def run(interval_minutes: int):
    log.info("=" * 60)
    log.info("Palaiseau Appointment Checker  |  interval=%dm", interval_minutes)
    log.info("=" * 60)

    last_notified_available = False

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

        # Main polling loop
        while True:
            result = _check_slots(page)

            if result is None:
                # Session expired — need CAPTCHA again
                _notify_session_expired()
                log.info("Waiting for CAPTCHA to be solved again…")
                if not _wait_for_captcha_solve(page):
                    log.error("Could not recover — exiting.")
                    break
                last_notified_available = False

            elif result is True:
                log.info("*** SLOTS AVAILABLE — sending notification ***")
                if not last_notified_available:
                    _notify_slots_available(page.url)
                    last_notified_available = True
                else:
                    log.info("(already notified about this availability — skipping repeat email)")

            else:
                # No slots — reset notification flag so we'll notify again next time they appear
                last_notified_available = False

            log.info("Next check in %d minute(s). Press Ctrl+C to stop.", interval_minutes)
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
