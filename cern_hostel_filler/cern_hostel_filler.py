#!/usr/bin/env python3
"""
CERN Hostel Reservation Gap Filler
===================================
Automatically fills gaps in your CERN hostel reservations by extending
neighboring bookings to cover a target date range.

Usage:
    python cern_hostel_filler.py [--dry-run] [--headless]

First run: a browser window will open. Log in with your CERN SSO + Google
Authenticator 2FA, then press Enter in the terminal. The session is saved
to a persistent profile, so subsequent runs won't need 2FA (until CERN
expires the session).

Dependencies:
    pip install playwright beautifulsoup4
    playwright install chromium
"""

import argparse
import json
import logging
import re
import sys
import time
from datetime import date, timedelta
from pathlib import Path

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

from gmail_notifier import GmailNotifier

# ─────────────────────────────────────────────
#  USER CONFIGURATION  ← edit this section
# ─────────────────────────────────────────────

# The continuous date range you want to be covered at the hostel.
# The script will auto-detect gaps between your existing reservations
# that fall within this window and try to fill them.
TARGET_START = date(2026, 7, 1)
TARGET_END   = date(2026, 8, 30)

# Email / notification settings
NOTIFY_EMAIL    = "dyn040294@gmail.com"
# Path to a plain-text file with two lines: gmail address, then app password.
# If the file doesn't exist, email notifications are silently skipped.
GMAIL_CRED_PATH = Path.home() / "Desktop/creds/gmail_cred.txt"

# How often to recheck (minutes)
CHECK_INTERVAL_MINUTES = 30

# How long to wait (seconds) for the page to load after submitting a form
PAGE_LOAD_TIMEOUT = 15_000  # ms (Playwright uses ms)

# Path where the browser profile (cookies/session) will be stored
PROFILE_DIR = Path.home() / ".cern_hostel_profile"

# The reservation portal URL
PORTAL_URL = "https://hostel.cern.ch/Reservations"

# Log file
LOG_FILE = Path("cern_hostel_filler.log")

# ─────────────────────────────────────────────
#  END OF USER CONFIGURATION
# ─────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
    ],
)
log = logging.getLogger(__name__)


# ── Date helpers ──────────────────────────────────────────────────────────────

def date_range(start: date, end: date):
    """Yields every date from start up to (but not including) end."""
    d = start
    while d < end:
        yield d
        d += timedelta(days=1)


def parse_error_dates(error_text: str) -> set[date]:
    """
    Extract unavailable dates from the portal error string, e.g.
    'Not enough available [28.06.2026, 29.06.2026, 30.06.2026]'
    Returns a set of date objects.
    """
    unavailable = set()
    # Matches DD.MM.YYYY
    for m in re.finditer(r"(\d{2})\.(\d{2})\.(\d{4})", error_text):
        d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        unavailable.add(date(y, mo, d))
    return unavailable


# ── HTML parsing ──────────────────────────────────────────────────────────────

def parse_reservations(html: str) -> list[dict]:
    """
    Parse the 'My Reservations' page HTML and return a list of active
    (modifiable) reservations, each as:
        {
            "id":       str,        # confirmation number, e.g. "1050810"
            "from":     date,
            "to":       date,
            "made_for": str,        # hidden madeFor value (person ID)
            "modifiable": bool,     # True if 'Apply changes' button exists
        }
    Only reservations with an editable from/to date input (no readonly attr)
    are returned – those are the ones you can modify.
    """
    soup = BeautifulSoup(html, "html.parser")
    reservations = []

    # Each modifiable reservation has a hidden cancelId input
    for cancel_input in soup.find_all("input", {"name": re.compile(r"^cancelId$")}):
        res_id = cancel_input["value"]

        from_input = soup.find("input", {"name": f"from{res_id}"})
        to_input   = soup.find("input", {"name": f"to{res_id}"})

        if not from_input or not to_input:
            continue

        # readonly inputs exist but can't be submitted – skip them
        if from_input.get("readonly") or to_input.get("readonly"):
            continue

        made_for_input = cancel_input.find_next("input", {"name": "madeFor"})
        made_for = made_for_input["value"] if made_for_input else ""

        try:
            from_date = date.fromisoformat(from_input["value"])
            to_date   = date.fromisoformat(to_input["value"])
        except (KeyError, ValueError):
            log.warning("Could not parse dates for reservation %s – skipping.", res_id)
            continue

        reservations.append({
            "id":         res_id,
            "from":       from_date,
            "to":         to_date,
            "made_for":   made_for,
            "modifiable": True,
        })

    reservations.sort(key=lambda r: r["from"])
    return reservations


def parse_errors(html: str) -> str:
    """Return the text content of the #errors div (empty string if none)."""
    soup = BeautifulSoup(html, "html.parser")
    errors_div = soup.find(id="errors")
    if errors_div:
        return errors_div.get_text(separator=" ").strip()
    return ""


# ── Gap detection ─────────────────────────────────────────────────────────────

def find_gaps(reservations: list[dict], target_start: date, target_end: date) -> list[dict]:
    """
    Given a sorted list of reservations, find contiguous date ranges within
    [target_start, target_end) that are not covered by any reservation.

    Returns a list of gap dicts:
        {
            "gap_start":  date,          # first uncovered night
            "gap_end":    date,          # last uncovered night (inclusive)
            "prev_res":   dict | None,   # reservation immediately before the gap
            "next_res":   dict | None,   # reservation immediately after the gap
        }
    """
    # Build a set of covered nights within the target window
    covered = set()
    for r in reservations:
        for d in date_range(r["from"], r["to"]):   # 'to' is checkout = last covered night is to-1
            if target_start <= d < target_end:
                covered.add(d)

    # Find contiguous uncovered stretches
    all_nights = list(date_range(target_start, target_end))
    gaps = []
    i = 0
    while i < len(all_nights):
        if all_nights[i] not in covered:
            gap_start = all_nights[i]
            while i < len(all_nights) and all_nights[i] not in covered:
                i += 1
            gap_end = all_nights[i - 1]  # inclusive

            # Find neighboring reservations
            prev_res = next(
                (r for r in reversed(reservations) if r["to"] <= gap_start and r["modifiable"]),
                None,
            )
            next_res = next(
                (r for r in reservations if r["from"] > gap_end and r["modifiable"]),
                None,
            )

            gaps.append({
                "gap_start": gap_start,
                "gap_end":   gap_end,
                "prev_res":  prev_res,
                "next_res":  next_res,
            })
        else:
            i += 1

    return gaps


# ── Browser helpers ───────────────────────────────────────────────────────────

def wait_for_reservations_page(page, timeout=PAGE_LOAD_TIMEOUT):
    """Wait until the #content div with the reservations table is visible."""
    page.wait_for_selector("#content.Reservations", timeout=timeout)


def submit_modify(page, res_id: str, new_from: date, new_to: date, dry_run: bool) -> str:
    """
    Modify a single reservation's dates via the web form.
    Returns the error string from the page after submission (empty = success).

    The form structure (from the HTML):
        <form action="https://hostel.cern.ch/Reservations" method="post">
            <input name="from{id}" type="date" value="...">
            <input name="to{id}"   type="date" value="...">
            <input name="cancelId" value="{id}">
            <input name="madeFor"  value="{person_id}">
            <input type="submit" name="modifyButton" value="Apply changes"
                   onclick="return confirmPopupAnimation(...)">
        </form>

    Playwright approach: fill the date inputs, then click Apply changes and
    accept the confirm() dialog.
    """
    log.info(
        "  %s reservation %s: %s → %s  (from=%s to=%s)",
        "DRY-RUN – would modify" if dry_run else "Modifying",
        res_id,
        "from", "to",
        new_from.isoformat(),
        new_to.isoformat(),
    )

    if dry_run:
        return ""

    # Fill the 'from' date input
    from_selector = f'input[name="from{res_id}"]'
    to_selector   = f'input[name="to{res_id}"]'

    page.fill(from_selector, new_from.isoformat())
    page.fill(to_selector,   new_to.isoformat())

    # The onclick fires a confirm() dialog – auto-accept it
    page.once("dialog", lambda dialog: dialog.accept())

    # Click "Apply changes"
    modify_btn_selector = f'input[name="modifyButton"][onclick*="{res_id}"]'
    page.click(modify_btn_selector)

    # Wait for the page to reload
    try:
        wait_for_reservations_page(page, timeout=PAGE_LOAD_TIMEOUT)
    except PlaywrightTimeoutError:
        log.error("Timed out waiting for page reload after modify – check manually.")
        return "TIMEOUT"

    html = page.content()
    return parse_errors(html)


# ── Binary-search for furthest available date ─────────────────────────────────

def find_furthest_available(
    page,
    res: dict,
    extend_which: str,          # "to" or "from"
    target_date: date,          # the ideal boundary we'd like to reach
    base_date: date,            # current value of the other boundary (unchanged)
    dry_run: bool,
) -> date | None:
    """
    Binary-search between the current boundary and target_date to find the
    furthest date we can successfully extend to.

    extend_which: "to"   → we're pushing the checkout date forward
                  "from" → we're pulling the check-in date backward

    Returns the furthest reachable date, or None if not even 1 day is available.
    """
    if extend_which == "to":
        lo = res["to"]          # current checkout (already confirmed available)
        hi = target_date        # ideal new checkout
    else:
        lo = target_date        # ideal new check-in (earlier)
        hi = res["from"]        # current check-in (already confirmed available)

    best = None

    while True:
        if extend_which == "to":
            if lo >= hi:
                break
            mid = lo + (hi - lo) // 2
            new_from, new_to = base_date, mid
        else:
            if lo >= hi:
                break
            mid = lo + (hi - lo) // 2
            new_from, new_to = mid, base_date

        err = submit_modify(page, res["id"], new_from, new_to, dry_run)
        unavail = parse_error_dates(err) if err else set()

        if extend_which == "to":
            if not (unavail & set(date_range(res["to"], mid))):
                # success up to mid
                best = mid
                lo = mid + timedelta(days=1)
            else:
                hi = mid
        else:
            if not (unavail & set(date_range(mid, res["from"]))):
                best = mid
                hi = mid
            else:
                lo = mid + timedelta(days=1)

        # Re-parse reservations after each attempt to keep res["from"/"to"] updated
        html = page.content()
        updated = parse_reservations(html)
        for r in updated:
            if r["id"] == res["id"]:
                res["from"] = r["from"]
                res["to"]   = r["to"]
                break

    return best


# ── Single check cycle ────────────────────────────────────────────────────────

def _run_check(page, dry_run: bool):
    """Parse reservations, fill gaps, print summary, send notification."""
    # ── Step 2: parse current reservations ───────────────────────────────
    html = page.content()
    reservations = parse_reservations(html)

    if not reservations:
        log.warning("No modifiable reservations found. Check that you are on the right tab.")
        return

    log.info("Found %d modifiable reservation(s):", len(reservations))
    for r in reservations:
        log.info("  #%s  %s → %s", r["id"], r["from"], r["to"])

    # ── Step 3: detect gaps ───────────────────────────────────────────────
    gaps = find_gaps(reservations, TARGET_START, TARGET_END)

    if not gaps:
        log.info("No gaps found within %s – %s. Nothing to do.", TARGET_START, TARGET_END)
        return

    log.info("Detected %d gap(s):", len(gaps))
    for g in gaps:
        prev_id = g["prev_res"]["id"] if g["prev_res"] else "none"
        next_id = g["next_res"]["id"] if g["next_res"] else "none"
        log.info(
            "  Gap: %s – %s  (prev_res=#%s, next_res=#%s)",
            g["gap_start"], g["gap_end"], prev_id, next_id,
        )

    # ── Step 4: attempt to fill each gap ─────────────────────────────────
    gap_summaries = []   # list of {"label": str, "actions": [str], "result": str}

    for gap in gaps:
        gap_start = gap["gap_start"]
        gap_end   = gap["gap_end"]
        gap_label = f"{gap_start} – {gap_end}"
        log.info("─" * 50)
        log.info("Working on gap: %s", gap_label)

        cur_gap = {"label": gap_label, "actions": [], "result": "no change"}

        prev_res = gap["prev_res"]
        next_res = gap["next_res"]

        # Strategy: prefer extending the reservation that ENDS just before
        # the gap (push its 'to' forward). Fall back to pulling the
        # reservation that STARTS just after (pull its 'from' backward).
        # If both exist, try extending 'prev' first to cover the whole gap;
        # if that only partially works, extend 'next' to meet the new 'prev' end.

        filled_start = gap_start
        filled_end   = gap_end

        # --- Try extending prev_res.to → gap_end + 1 (checkout = day after last night) ---
        if prev_res:
            ideal_to = gap_end + timedelta(days=1)   # checkout date
            log.info(
                "  Attempting to extend #%s 'to' from %s → %s",
                prev_res["id"], prev_res["to"], ideal_to,
            )
            err = submit_modify(
                page, prev_res["id"],
                new_from=prev_res["from"],
                new_to=ideal_to,
                dry_run=dry_run,
            )

            if not err:
                log.info("  ✓ Success! Gap %s fully filled by extending #%s.", gap_label, prev_res["id"])
                cur_gap["actions"].append(
                    f"Extended #{prev_res['id']} 'to' → {ideal_to}  ✓  gap fully covered"
                )
                cur_gap["result"] = "filled"
                gap_summaries.append(cur_gap)
                # Refresh reservations
                html = page.content()
                reservations = parse_reservations(html)
                continue  # next gap

            # Partial failure – find furthest reachable date
            unavail = parse_error_dates(err)
            log.info("  Partial failure. Unavailable dates: %s", sorted(unavail))

            # The available dates are those in [gap_start, ideal_to) NOT in unavail
            attempted_nights = set(date_range(gap_start, ideal_to))
            available_new    = attempted_nights - unavail

            if available_new:
                furthest = max(available_new)
                log.info("  Searching for furthest available date (binary search) …")
                furthest_to = find_furthest_available(
                    page, prev_res,
                    extend_which="to",
                    target_date=ideal_to,
                    base_date=prev_res["from"],
                    dry_run=dry_run,
                )
                if furthest_to:
                    log.info(
                        "  ✓ Extended #%s to %s (covers through %s).",
                        prev_res["id"], furthest_to, furthest_to - timedelta(days=1),
                    )
                    filled_start = furthest_to  # new gap start (if any remains)
                    cur_gap["actions"].append(
                        f"Extended #{prev_res['id']} 'to' → {furthest_to} "
                        f"(covers through {furthest_to - timedelta(days=1)}; "
                        f"remaining gap starts {furthest_to})"
                    )
                    cur_gap["result"] = "partially filled"
                else:
                    log.info("  Could not extend #%s at all – dates available but not adjacent.", prev_res["id"])
                    cur_gap["actions"].append(
                        f"Dates available in gap but not reachable from #{prev_res['id']} 'to' – manual booking needed"
                    )
                    cur_gap["result"] = "available_not_adjacent"
            else:
                log.info("  No dates available in gap range for extending #%s.", prev_res["id"])
                cur_gap["actions"].append(
                    f"Tried to extend #{prev_res['id']} 'to' → {ideal_to}: "
                    f"all gap dates unavailable, reservation unchanged"
                )

            # Refresh after binary search
            html = page.content()
            reservations = parse_reservations(html)
            for r in reservations:
                if r["id"] == prev_res["id"]:
                    prev_res = r

        # --- If a gap (or remaining gap) still exists, try next_res.from ---
        # Check if the gap is now fully covered
        remaining_gap_nights = set(date_range(filled_start, gap_end + timedelta(days=1)))
        covered_now = set()
        for r in reservations:
            for d in date_range(r["from"], r["to"]):
                covered_now.add(d)
        remaining_gap_nights -= covered_now

        if remaining_gap_nights and next_res:
            new_gap_start = min(remaining_gap_nights)
            log.info(
                "  Attempting to extend #%s 'from' backward from %s → %s",
                next_res["id"], next_res["from"], new_gap_start,
            )
            err2 = submit_modify(
                page, next_res["id"],
                new_from=new_gap_start,
                new_to=next_res["to"],
                dry_run=dry_run,
            )
            if not err2:
                log.info("  ✓ Filled remaining gap by pulling #%s 'from' to %s.", next_res["id"], new_gap_start)
                cur_gap["actions"].append(
                    f"Extended #{next_res['id']} 'from' → {new_gap_start}  ✓  remaining gap covered"
                )
                cur_gap["result"] = "filled"
            else:
                unavail2 = parse_error_dates(err2)
                available2 = remaining_gap_nights - unavail2
                if available2:
                    furthest_from = min(available2)  # earliest available check-in
                    log.info(
                        "  Partial – earliest available check-in for #%s: %s",
                        next_res["id"], furthest_from,
                    )
                    reached = find_furthest_available(
                        page, next_res,
                        extend_which="from",
                        target_date=new_gap_start,
                        base_date=next_res["to"],
                        dry_run=dry_run,
                    )
                    if reached:
                        cur_gap["actions"].append(
                            f"Extended #{next_res['id']} 'from' as far back as possible "
                            f"(some nights still unavailable: {sorted(unavail2)})"
                        )
                        if cur_gap["result"] == "no change":
                            cur_gap["result"] = "partially filled"
                    else:
                        log.info("  Dates available but not adjacent to #%s 'from' – manual booking needed.", next_res["id"])
                        cur_gap["actions"].append(
                            f"Dates available in gap but not reachable from #{next_res['id']} 'from' – manual booking needed"
                        )
                        if cur_gap["result"] == "no change":
                            cur_gap["result"] = "available_not_adjacent"
                else:
                    log.info("  Could not extend #%s from either.", next_res["id"])
                    cur_gap["actions"].append(
                        f"Tried to extend #{next_res['id']} 'from' → {new_gap_start}: "
                        f"all dates unavailable, reservation unchanged"
                    )

            html = page.content()
            reservations = parse_reservations(html)

        elif remaining_gap_nights:
            log.info("  No next_res to extend into remaining gap %s. Dates still open: %s",
                     gap_label, sorted(remaining_gap_nights))
            cur_gap["actions"].append("No adjacent reservation on the right side to extend")

        if not cur_gap["actions"]:
            cur_gap["actions"].append("No adjacent reservations found on either side; nothing attempted")

        gap_summaries.append(cur_gap)

    # ── Step 5: print summary ─────────────────────────────────────────────
    log.info("=" * 60)
    log.info("ACTIONS")
    log.info("=" * 60)
    any_change = any(gs["result"] != "no change" for gs in gap_summaries)
    for gs in gap_summaries:
        log.info("  Gap %s  [%s]", gs["label"], gs["result"].upper())
        for action in gs["actions"]:
            log.info("    • %s", action)
    if not any_change:
        log.info("")
        log.info("  No reservations were modified this run.")

    # Final state of reservations
    html = page.content()
    final_reservations = parse_reservations(html)
    log.info("")
    log.info("Final reservations:")
    for r in final_reservations:
        log.info("  #%s  %s → %s", r["id"], r["from"], r["to"])

    remaining_gaps = find_gaps(final_reservations, TARGET_START, TARGET_END)
    if remaining_gaps:
        log.info("")
        log.info("Remaining gaps (could not be filled):")
        for g in remaining_gaps:
            log.info("  %s – %s", g["gap_start"], g["gap_end"])
    else:
        log.info("Target range fully covered! 🎉")

    # ── Step 6: email notification ────────────────────────────────────────
    _send_notification(gap_summaries, remaining_gaps, final_reservations, dry_run)


# ── Main loop ─────────────────────────────────────────────────────────────────

def run(dry_run: bool, headless: bool, interval_minutes: int):
    log.info("=" * 60)
    log.info("CERN Hostel Gap Filler  |  target: %s → %s", TARGET_START, TARGET_END)
    log.info("dry-run=%s  headless=%s  interval=%dm", dry_run, headless, interval_minutes)
    log.info("=" * 60)

    PROFILE_DIR.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as pw:
        browser = pw.chromium.launch_persistent_context(
            str(PROFILE_DIR),
            headless=headless,
            slow_mo=200,
        )
        page = browser.pages[0] if browser.pages else browser.new_page()

        first_run = True
        while True:
            if not first_run:
                log.info("=" * 60)
                log.info("Rechecking at %s", time.strftime("%Y-%m-%d %H:%M:%S"))
                log.info("=" * 60)

            # ── Step 1: navigate and handle login ────────────────────────────
            log.info("Navigating to %s …", PORTAL_URL)
            page.goto(PORTAL_URL, wait_until="domcontentloaded")

            try:
                wait_for_reservations_page(page, timeout=5_000)
                log.info("Session active%s.", " – skipping login" if first_run else "")
            except PlaywrightTimeoutError:
                if not first_run:
                    log.warning("Session expired – login required.")
                    _send_login_required_email()
                else:
                    log.info("Not logged in. A browser window should have opened.")
                log.info(
                    "Please log in with your CERN SSO + Google Authenticator 2FA,\n"
                    "navigate to the 'My Reservations' tab if needed, then come back\n"
                    "here and press ENTER to continue …"
                )
                input()
                wait_for_reservations_page(page, timeout=30_000)
                log.info("Login confirmed – session saved to %s", PROFILE_DIR)

            first_run = False

            _run_check(page, dry_run)

            log.info("Next check in %d minutes. Press Ctrl+C to stop.", interval_minutes)
            time.sleep(interval_minutes * 60)

        browser.close()


# ── Email notifications ────────────────────────────────────────────────────────

def _send_login_required_email():
    """Notify that the CERN SSO session has expired and manual login is needed."""
    if not GMAIL_CRED_PATH.exists():
        return
    subject = "[ACTION REQUIRED] CERN Hostel: session expired, login needed"
    body = (
        "The CERN Hostel Gap Filler is running but your CERN SSO session has expired.\n\n"
        "Please open the terminal where the script is running and log in again "
        "(CERN SSO + Google Authenticator 2FA), then press ENTER to resume.\n\n"
        "The script will continue automatically after you log in."
    )
    try:
        notifier = GmailNotifier(str(GMAIL_CRED_PATH))
        notifier.send_email(NOTIFY_EMAIL, subject, body)
        log.info("Login-required email sent to %s.", NOTIFY_EMAIL)
    except Exception as e:
        log.error("Failed to send login-required email: %s", e)




def _send_notification(gap_summaries, remaining_gaps, final_reservations, dry_run):
    """Send a summary email only when there is actual availability to report."""
    if not GMAIL_CRED_PATH.exists():
        log.info("No Gmail credentials found at %s – skipping email.", GMAIL_CRED_PATH)
        return

    any_extended      = any(gs["result"] in ("filled", "partially filled") for gs in gap_summaries)
    any_non_adjacent  = any(gs["result"] == "available_not_adjacent"       for gs in gap_summaries)

    if not any_extended and not any_non_adjacent:
        log.info("No availability found this run – skipping email.")
        return

    if any_non_adjacent:
        subject = "[ACTION REQUIRED] CERN Hostel: available dates need manual booking"
    else:
        subject = "[CERN Hostel] Reservation(s) extended automatically – no action needed"

    if dry_run:
        subject = "[DRY-RUN] " + subject

    lines = []

    if any_non_adjacent:
        lines.append(
            "Available dates were found in your CERN hostel gap(s) that cannot be filled\n"
            "automatically because they are not adjacent to an existing reservation.\n"
            "Please log in and book these manually:\n"
        )
        for gs in gap_summaries:
            if gs["result"] == "available_not_adjacent":
                lines.append(f"  • Gap {gs['label']}")
        lines.append("")

    if any_extended:
        intro = "The following gaps were also extended automatically:\n" if any_non_adjacent \
                else "The following gaps were extended automatically (no action needed):\n"
        lines.append(intro)
        for gs in gap_summaries:
            if gs["result"] in ("filled", "partially filled"):
                lines.append(f"  • Gap {gs['label']}  [{gs['result'].upper()}]")
                for action in gs["actions"]:
                    lines.append(f"      {action}")
        lines.append("")

    lines.append("Full action log:")
    for gs in gap_summaries:
        lines.append(f"  Gap {gs['label']}  [{gs['result'].upper()}]")
        for action in gs["actions"]:
            lines.append(f"    • {action}")

    lines.append("")
    lines.append("Current reservations:")
    for r in final_reservations:
        lines.append(f"  #{r['id']}  {r['from']} → {r['to']}")

    body = "\n".join(lines)

    try:
        notifier = GmailNotifier(str(GMAIL_CRED_PATH))
        notifier.send_email(NOTIFY_EMAIL, subject, body)
        log.info("Notification email sent to %s.", NOTIFY_EMAIL)
    except Exception as e:
        log.error("Failed to send notification email: %s", e)


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Fill CERN hostel reservation gaps.")
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Parse and detect gaps but do NOT submit any form changes.",
    )
    parser.add_argument(
        "--headless", action="store_true",
        help="Run browser in headless mode (no visible window). "
             "Only use this after the session is already established.",
    )
    parser.add_argument(
        "--interval", type=int, default=CHECK_INTERVAL_MINUTES, metavar="MINUTES",
        help=f"Minutes between checks (default: {CHECK_INTERVAL_MINUTES}).",
    )
    args = parser.parse_args()

    run(dry_run=args.dry_run, headless=args.headless, interval_minutes=args.interval)


if __name__ == "__main__":
    main()
