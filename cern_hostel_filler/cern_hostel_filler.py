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
import os
import re
import sys
import time
from datetime import date, timedelta
from pathlib import Path

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

from gmail_notifier import GmailNotifier
import login_server

# ─────────────────────────────────────────────
#  USER CONFIGURATION  ← edit this section
# ─────────────────────────────────────────────

# The continuous date range you want to be covered at the hostel.
# The script will auto-detect gaps between your existing reservations
# that fall within this window and try to fill them.
TARGET_START = date(2026, 6, 25)
TARGET_END   = date(2026, 8, 30)

# Email / notification settings
NOTIFY_EMAIL    = "dyn040294@gmail.com"
# Path to a plain-text file with two lines: gmail address, then app password.
# If the file doesn't exist, email notifications are silently skipped.
GMAIL_CRED_PATH = Path.home() / "Desktop/creds/gmail_cred.txt"

# Path to a plain-text file with CERN username on line 1 and password on line 2.
# When set, the login page will only ask for the 2FA code (username/password are
# pre-loaded), and the server will try to open an external SSH tunnel so it is
# reachable from outside your home network.
CERN_CREDS_PATH = Path.home() / "Desktop/creds/cern.txt"

# How often to recheck (minutes)
CHECK_INTERVAL_MINUTES = 30

# How long to wait (seconds) for the page to load after submitting a form
PAGE_LOAD_TIMEOUT = 15_000  # ms (Playwright uses ms)

# Path where the browser profile (cookies/session) will be stored
PROFILE_DIR = Path.home() / ".cern_hostel_profile"

# The reservation portal URL
PORTAL_URL = "https://hostel.cern.ch/Reservations"

# Port for the temporary login web server (open this in your phone browser)
LOGIN_SERVER_PORT = 5000

# Log file
LOG_FILE = Path("cern_hostel_filler.log")

# Availability plot — saved after every check cycle; also shown on the login page.
PLOT_PATH = Path("availability_plot.png")

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


def format_date_ranges(dates: list[date]) -> str:
    """
    Format a sorted list of dates as compact human-readable ranges.
    e.g. [Jul 17,18,19, Jul 23,24,25,26, Jul 29] → '7/17–7/19, 7/23–7/26, 7/29'
    """
    if not dates:
        return ""
    dates = sorted(dates)
    ranges: list[tuple[date, date]] = []
    start = end = dates[0]
    for d in dates[1:]:
        if d == end + timedelta(days=1):
            end = d
        else:
            ranges.append((start, end))
            start = end = d
    ranges.append((start, end))

    parts = []
    for s, e in ranges:
        if s == e:
            parts.append(f"{s.month}/{s.day}")
        else:
            parts.append(f"{s.month}/{s.day}–{e.month}/{e.day}")
    return ", ".join(parts)


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

        # Readonly inputs exist but can't be submitted.
        # We still include them so their nights count as covered in gap detection;
        # modifiable=False prevents them from being targeted for extension.
        is_modifiable = not (from_input.get("readonly") or to_input.get("readonly"))

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
            "modifiable": is_modifiable,
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
) -> tuple[date | None, set[date]]:
    """
    Binary-search between the current boundary and target_date to find the
    furthest date we can successfully extend to.

    extend_which: "to"   → we're pushing the checkout date forward
                  "from" → we're pulling the check-in date backward

    Returns (best_date, all_unavail) where:
      - best_date is the furthest reachable date, or None if no improvement possible
      - all_unavail is the union of every unavailable-date set seen during the search
        (callers should merge this into their own all_unavail_dates so the final
        potentially-bookable check is accurate)
    """
    if extend_which == "to":
        lo = res["to"]          # current checkout (already confirmed available)
        hi = target_date        # ideal new checkout
    else:
        lo = target_date        # ideal new check-in (earlier)
        hi = res["from"]        # current check-in (already confirmed available)

    # Remember starting boundary so we can reject "success" that didn't actually move.
    initial_boundary = res["to"] if extend_which == "to" else res["from"]

    best = None
    all_seen_unavail: set[date] = set()

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
        all_seen_unavail |= unavail

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

    # Only count as success if we actually moved the boundary.
    if extend_which == "to":
        best_result = best if (best is not None and best > initial_boundary) else None
    else:
        best_result = best if (best is not None and best < initial_boundary) else None

    return best_result, all_seen_unavail


# ── Automated CERN SSO login ──────────────────────────────────────────────────

def perform_login(page, username: str, password: str, totp: str) -> bool:
    """
    Drive Playwright through the CERN SSO (Keycloak) login flow.

    Page 1 (auth.cern.ch): username + password on the same page → click Sign In
    Page 2 (auth.cern.ch): OTP field (#otp) → click Sign In
    Then redirects back to the hostel portal.

    Returns True on success, False if any step times out.
    """
    try:
        # ── Page 1: username + password ───────────────────────────────────────
        log.info("Login: waiting for username/password page…")
        page.wait_for_selector("#username", timeout=30_000)
        page.fill("#username", username)
        page.fill("#password", password)
        page.click("#kc-login")
        log.info("Login: credentials submitted.")

        # ── Page 2: OTP ───────────────────────────────────────────────────────
        log.info("Login: waiting for OTP page…")
        page.wait_for_selector("#otp", timeout=30_000)
        page.fill("#otp", totp)
        page.click("#kc-login")
        log.info("Login: OTP submitted.")

        # ── Redirect back to portal ───────────────────────────────────────────
        log.info("Login: waiting for portal redirect…")
        wait_for_reservations_page(page, timeout=20_000)
        log.info("Login: success — session saved to %s", PROFILE_DIR)
        return True

    except PlaywrightTimeoutError as exc:
        log.error("Login: timed out — %s", exc)
        return False
    except Exception as exc:
        log.error("Login: unexpected error — %s", exc)
        return False


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
        all_unavail_dates: set[date] = set()   # union of all unavail sets seen this gap

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
            all_unavail_dates |= unavail
            log.info("  Partial failure. Unavailable dates: %s", sorted(unavail))

            # The available dates are those in [gap_start, ideal_to) NOT in unavail
            attempted_nights = set(date_range(gap_start, ideal_to))
            available_new    = attempted_nights - unavail

            if available_new:
                furthest = max(available_new)
                log.info("  Searching for furthest available date (binary search) …")
                furthest_to, bs_unavail = find_furthest_available(
                    page, prev_res,
                    extend_which="to",
                    target_date=ideal_to,
                    base_date=prev_res["from"],
                    dry_run=dry_run,
                )
                all_unavail_dates |= bs_unavail
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
                all_unavail_dates |= unavail2
                available2 = remaining_gap_nights - unavail2
                if available2:
                    furthest_from = min(available2)  # earliest available check-in
                    log.info(
                        "  Partial – earliest available check-in for #%s: %s",
                        next_res["id"], furthest_from,
                    )
                    reached, bs_unavail2 = find_furthest_available(
                        page, next_res,
                        extend_which="from",
                        target_date=new_gap_start,
                        base_date=next_res["to"],
                        dry_run=dry_run,
                    )
                    all_unavail_dates |= bs_unavail2
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

        # Final check: if the gap is only partially filled, see if any remaining
        # uncovered nights were NOT in any unavail set — those might be manually bookable.
        if cur_gap["result"] == "partially filled":
            html = page.content()
            reservations = parse_reservations(html)
            covered_final = set()
            for r in reservations:
                for d in date_range(r["from"], r["to"]):
                    covered_final.add(d)
            remaining_final = {
                d for d in date_range(gap_start, gap_end + timedelta(days=1))
                if d not in covered_final
            }
            potentially_bookable = remaining_final - all_unavail_dates
            if potentially_bookable:
                cur_gap["result"] = "partially filled + manual needed"
                cur_gap["manual_nights"] = sorted(potentially_bookable)
                cur_gap["actions"].append(
                    f"Remaining nights possibly available for manual booking: "
                    f"{sorted(potentially_bookable)}"
                )
                log.info(
                    "  Nights possibly available for manual booking: %s",
                    sorted(potentially_bookable),
                )

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

    return gap_summaries, remaining_gaps, final_reservations


# ── Script restart ────────────────────────────────────────────────────────────

def _restart_script():
    """
    Replace the current process with a fresh instance of itself.
    Called as a last resort when the login/check cycle is stuck beyond recovery.
    Does not return.
    """
    log.warning("Restarting script completely via os.execv…")
    try:
        os.execv(sys.executable, [sys.executable] + sys.argv)
    except Exception as exc:
        log.error("os.execv failed (%s) — exiting instead.", exc)
        sys.exit(1)


# ── Main loop ─────────────────────────────────────────────────────────────────

def run(dry_run: bool, headless: bool, interval_minutes: int, show_plot: bool = False):
    log.info("=" * 60)
    log.info("CERN Hostel Gap Filler  |  target: %s → %s", TARGET_START, TARGET_END)
    log.info("dry-run=%s  headless=%s  interval=%dm", dry_run, headless, interval_minutes)
    log.info("=" * 60)

    PROFILE_DIR.mkdir(parents=True, exist_ok=True)

    # How long to wait (seconds) for the user to click Connect before restarting.
    CONNECT_TIMEOUT_SECONDS = 4 * 3600   # 4 hours
    # How long to wait (seconds) for the user to enter their TOTP after Connect.
    TOTP_TIMEOUT_SECONDS    = 5 * 60     # 5 minutes

    def _open_browser(pw):
        b = pw.chromium.launch_persistent_context(
            str(PROFILE_DIR),
            headless=headless,
            slow_mo=200,
        )
        p = b.pages[0] if b.pages else b.new_page()
        return b, p

    def _close_browser(browser):
        if browser is not None:
            try:
                browser.close()
            except Exception as e:
                log.warning("Error closing browser: %s", e)
        return None, None

    with sync_playwright() as pw:
        browser, page = _open_browser(pw)

        first_run = True
        consecutive_failures = 0
        MAX_RETRIES = 3
        RETRY_DELAY_SECONDS = 60

        while True:
            if not first_run:
                log.info("=" * 60)
                log.info("Rechecking at %s", time.strftime("%Y-%m-%d %H:%M:%S"))
                log.info("=" * 60)

            attempt = 0
            success = False
            last_error = None
            login_srv = None

            while attempt < MAX_RETRIES:
                try:
                    # ── Step 1: navigate and handle login ────────────────────
                    if browser is None:
                        browser, page = _open_browser(pw)

                    log.info("Navigating to %s …", PORTAL_URL)
                    page.goto(PORTAL_URL, wait_until="domcontentloaded")

                    try:
                        wait_for_reservations_page(page, timeout=5_000)
                        log.info("Session active%s.", " – skipping login" if first_run else "")

                    except PlaywrightTimeoutError:
                        if not first_run:
                            log.warning("Session expired – login required.")
                        else:
                            log.info("Not logged in – starting login flow.")

                        # ── Close stale browser session ───────────────────────
                        browser, page = _close_browser(browser)

                        # ── Start login server (shows Connect button) ─────────
                        if login_srv is None:
                            login_srv = login_server.LoginServer(
                                port=LOGIN_SERVER_PORT,
                                creds_file=CERN_CREDS_PATH if CERN_CREDS_PATH.exists() else None,
                                plot_path=PLOT_PATH,
                            )
                            login_srv.start(on_ready=_send_login_required_email)

                        # ── Inner loop: Connect → fresh browser → 2FA → login ─
                        login_succeeded = False
                        while not login_succeeded:
                            # Wait for user to click the Connect button
                            log.info(
                                "Waiting for user to click Connect "
                                "(timeout: %d h)…", CONNECT_TIMEOUT_SECONDS // 3600
                            )
                            connected = login_srv.wait_for_connect(
                                timeout=CONNECT_TIMEOUT_SECONDS
                            )
                            if not connected:
                                log.error(
                                    "Timed out waiting for Connect after %d hours — "
                                    "restarting script.", CONNECT_TIMEOUT_SECONDS // 3600
                                )
                                login_srv.push_status(
                                    "Timed out — restarting the system.", kind="error"
                                )
                                login_srv.shutdown()
                                _restart_script()  # does not return

                            # Open a fresh playwright browser
                            log.info("User clicked Connect — opening fresh browser session…")
                            login_srv.push_status("Opening browser session…")
                            try:
                                browser, page = _open_browser(pw)
                                page.goto(PORTAL_URL, wait_until="domcontentloaded")
                                login_srv.push_status(
                                    "Browser ready — enter your 2FA code now."
                                )
                                login_srv.signal_session_ready()  # redirect → /2fa
                            except Exception as exc:
                                log.error("Failed to open browser session: %s", exc)
                                login_srv.push_status(
                                    f"Browser error: {exc} — please try Connect again.",
                                    kind="error",
                                )
                                login_srv.push_redirect_home()
                                browser, page = _close_browser(browser)
                                continue  # back to wait_for_connect

                            # Wait for 2FA code (short timeout — code expires in 30 s)
                            log.info(
                                "Waiting for 2FA submission (timeout: %ds)…",
                                TOTP_TIMEOUT_SECONDS,
                            )
                            creds = login_srv.wait_for_credentials(
                                timeout=TOTP_TIMEOUT_SECONDS
                            )
                            if creds is None:
                                log.warning(
                                    "Timed out waiting for 2FA (%ds) — "
                                    "closing browser and asking user to reconnect.",
                                    TOTP_TIMEOUT_SECONDS,
                                )
                                login_srv.push_status(
                                    "Timed out waiting for 2FA — please click Connect again.",
                                    kind="error",
                                )
                                login_srv.push_redirect_home()
                                browser, page = _close_browser(browser)
                                continue  # back to wait_for_connect

                            # Drive playwright through CERN SSO login
                            login_srv.push_status("Logging in to CERN SSO…")
                            login_ok = perform_login(
                                page,
                                username=creds["username"],
                                password=creds["password"],
                                totp=creds["totp"],
                            )
                            if not login_ok:
                                log.warning(
                                    "Login automation failed — closing browser and "
                                    "asking user to reconnect."
                                )
                                login_srv.push_status(
                                    "Login automation failed — please click Connect again.",
                                    kind="error",
                                )
                                login_srv.push_redirect_home()
                                browser, page = _close_browser(browser)
                                continue  # back to wait_for_connect

                            login_succeeded = True
                            login_srv.push_status(
                                "Login successful! Checking reservations…", kind="success"
                            )
                        # ── end inner login loop ──────────────────────────────

                    first_run = False

                    if login_srv:
                        login_srv.push_status("Scanning reservations…")
                    result = _run_check(page, dry_run)

                    if result:
                        gap_summaries, remaining_gaps, final_reservations = result
                        _show_plot(
                            final_reservations, gap_summaries, remaining_gaps,
                            show=show_plot,
                        )
                        if login_srv:
                            login_srv.push_status("", kind="plot_updated")
                            if remaining_gaps:
                                gaps_str = ", ".join(
                                    f"{g['gap_start']} – {g['gap_end']}"
                                    for g in remaining_gaps
                                )
                                login_srv.push_status(
                                    f"Remaining gaps: {gaps_str}", kind="warning"
                                )
                            else:
                                login_srv.push_status(
                                    "Target range fully covered!", kind="success"
                                )
                            login_srv.push_status(
                                f"Next check in {interval_minutes} minutes.", kind="done"
                            )

                    success = True
                    consecutive_failures = 0
                    break

                except KeyboardInterrupt:
                    raise
                except Exception as exc:
                    attempt += 1
                    last_error = exc
                    log.error(
                        "Error during check (attempt %d/%d): %s: %s",
                        attempt, MAX_RETRIES, type(exc).__name__, exc,
                    )
                    # Close browser so the next attempt starts fresh
                    browser, page = _close_browser(browser)
                    if attempt < MAX_RETRIES:
                        log.info("Retrying in %d seconds …", RETRY_DELAY_SECONDS)
                        time.sleep(RETRY_DELAY_SECONDS)
                    else:
                        log.error("All %d attempts failed.", MAX_RETRIES)

            if login_srv:
                if not success:
                    login_srv.push_status(
                        "All check attempts failed — will retry next cycle.", kind="error"
                    )
                time.sleep(5)   # give the phone a moment to read the final status
                login_srv.shutdown()
                login_srv = None

            if not success:
                consecutive_failures += 1
                log.error(
                    "Consecutive failure count: %d. Last error: %s: %s",
                    consecutive_failures, type(last_error).__name__, last_error,
                )
                _send_error_email(consecutive_failures, last_error)
                # After enough consecutive failures, restart entirely to clear any
                # stuck state (browser process leaks, broken playwright context, etc.)
                if consecutive_failures >= MAX_RETRIES * 2:
                    log.error(
                        "%d consecutive failures — restarting script.", consecutive_failures
                    )
                    _restart_script()

            # Ensure browser is open for next check cycle
            if browser is None:
                try:
                    browser, page = _open_browser(pw)
                except Exception as exc:
                    log.error("Could not reopen browser before sleep: %s", exc)

            log.info("Next check in %d minutes. Press Ctrl+C to stop.", interval_minutes)
            time.sleep(interval_minutes * 60)

        _close_browser(browser)


# ── Email notifications ────────────────────────────────────────────────────────

def _send_login_required_email(url: str = ""):
    """Notify that the CERN SSO session has expired, including the login URL."""
    log.info("Login required. Open %s on your phone.", url or f"http://localhost:{LOGIN_SERVER_PORT}")
    if not GMAIL_CRED_PATH.exists():
        return
    subject = "[ACTION REQUIRED] CERN Hostel: login required"
    body = (
        "The CERN Hostel Gap Filler needs you to log in to CERN SSO.\n\n"
        f"Open this link on your phone:\n\n    {url}\n\n"
        "1. Tap the Connect button — this starts a fresh browser session.\n"
        "2. On the 2FA page, open Google Authenticator LAST (code expires in 30 s),\n"
        "   then tap Submit.\n\n"
        "The script will continue automatically once you submit the 2FA form.\n"
        "If login fails, the page will return you to the Connect button to retry."
    )
    try:
        notifier = GmailNotifier(str(GMAIL_CRED_PATH))
        notifier.send_email(NOTIFY_EMAIL, subject, body)
        log.info("Login-required email sent to %s.", NOTIFY_EMAIL)
    except Exception as e:
        log.error("Failed to send login-required email: %s", e)


def _send_error_email(consecutive_failures: int, error: Exception):
    """Send an alert email when repeated check attempts all fail."""
    if not GMAIL_CRED_PATH.exists():
        return
    subject = f"[ACTION REQUIRED] CERN Hostel: script error ({consecutive_failures} consecutive failure(s))"
    body = (
        f"The CERN Hostel Gap Filler has failed {consecutive_failures} consecutive check(s).\n\n"
        f"Last error:\n  {type(error).__name__}: {error}\n\n"
        "The script will keep retrying every 30 minutes. "
        "You may need to check network connectivity or restart the script."
    )
    try:
        notifier = GmailNotifier(str(GMAIL_CRED_PATH))
        notifier.send_email(NOTIFY_EMAIL, subject, body)
        log.info("Error alert email sent to %s.", NOTIFY_EMAIL)
    except Exception as e:
        log.error("Failed to send error alert email: %s", e)


def _send_notification(gap_summaries, remaining_gaps, final_reservations, dry_run):
    """Send a summary email only when there is actual availability to report."""
    if not GMAIL_CRED_PATH.exists():
        log.info("No Gmail credentials found at %s – skipping email.", GMAIL_CRED_PATH)
        return

    any_extended     = any(gs["result"] in ("filled", "partially filled",
                                            "partially filled + manual needed")
                          for gs in gap_summaries)
    any_non_adjacent = any(gs["result"] in ("available_not_adjacent",
                                            "partially filled + manual needed")
                          for gs in gap_summaries)

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
            elif gs["result"] == "partially filled + manual needed":
                nights = gs.get("manual_nights", [])
                lines.append(
                    f"  • Gap {gs['label']}  (partially extended; "
                    f"book manually: {format_date_ranges(nights)})"
                )
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


# ── Timeline plot ─────────────────────────────────────────────────────────────

_mpl_backend_set = False


def _show_plot(final_reservations, gap_summaries, remaining_gaps, show: bool = False):
    global _mpl_backend_set
    try:
        import matplotlib
        if not _mpl_backend_set:
            if not show:
                matplotlib.use("Agg")   # headless — savefig works, show() is a no-op
            _mpl_backend_set = True
        import matplotlib.pyplot as plt
        import matplotlib.patches as mpatches
        import matplotlib.dates as mdates
        from datetime import datetime as _dt
    except ImportError:
        log.error("matplotlib not found — install it: pip install matplotlib")
        return

    def to_mdate(d: date):
        return mdates.date2num(_dt(d.year, d.month, d.day))

    # Nights covered by final reservations
    covered: set[date] = set()
    for r in final_reservations:
        for d in date_range(r["from"], r["to"]):
            if TARGET_START <= d < TARGET_END:
                covered.add(d)

    # Nights flagged as possibly manually bookable
    manual_nights: set[date] = set()
    for gs in gap_summaries:
        manual_nights.update(gs.get("manual_nights", []))

    def night_color(d: date) -> str:
        if d in covered:
            return "#2a7ab5"   # blue  – booked
        if d in manual_nights:
            return "#e88c1a"   # orange – possibly bookable manually
        return "#cc4444"       # red   – unavailable / unfilled

    # Group consecutive nights with the same color into (start, width_days, color) spans
    def make_spans(nights):
        spans = []
        if not nights:
            return spans
        seg_start = nights[0]
        seg_color = night_color(nights[0])
        for d in nights[1:]:
            c = night_color(d)
            if c != seg_color:
                spans.append((seg_start, (d - seg_start).days, seg_color))
                seg_start, seg_color = d, c
        spans.append((seg_start, (nights[-1] - seg_start).days + 1, seg_color))
        return spans

    all_nights = list(date_range(TARGET_START, TARGET_END))
    coverage_spans = make_spans(all_nights)

    # ── Layout: top panel = coverage band, bottom panels = per-reservation rows ──
    n_res = len(final_reservations)
    fig_height = 2.8 + n_res * 0.55
    fig, (ax_top, ax_bot) = plt.subplots(
        2, 1,
        figsize=(15, fig_height),
        gridspec_kw={"height_ratios": [1.6, max(n_res, 1)]},
        sharex=True,
    )

    # ── Top: coverage band ────────────────────────────────────────────────────
    for seg_start, width_days, color in coverage_spans:
        ax_top.broken_barh(
            [(to_mdate(seg_start), width_days)],
            (0.1, 0.8),
            facecolors=color, edgecolors="white", linewidth=0.3,
        )

    ax_top.set_ylim(0, 1)
    ax_top.set_yticks([0.5])
    ax_top.set_yticklabels(["Coverage"])
    ax_top.set_title(
        f"CERN Hostel Timeline  ·  {TARGET_START} – {TARGET_END - timedelta(days=1)}",
        fontweight="bold", pad=8,
    )

    # Legend
    legend_handles = [
        mpatches.Patch(color="#2a7ab5", label="Booked"),
        mpatches.Patch(color="#e8c61a", label="Possibly bookable (manual)"),
        mpatches.Patch(color="#cc4444", label="Unavailable / unfilled"),
    ]
    ax_top.legend(handles=legend_handles, loc="upper right", fontsize=8, framealpha=0.9)

    # ── Bottom: one row per reservation ──────────────────────────────────────
    for i, r in enumerate(final_reservations):
        vis_start = max(r["from"], TARGET_START)
        vis_end   = min(r["to"],   TARGET_END)
        if vis_start >= vis_end:
            continue
        width = (vis_end - vis_start).days
        ax_bot.broken_barh(
            [(to_mdate(vis_start), width)],
            (i + 0.1, 0.8),
            facecolors="#2a7ab5", edgecolors="white", linewidth=0.5,
        )
        # Label: reservation ID centred in the bar
        label_x = to_mdate(vis_start) + width / 2
        ax_bot.text(
            label_x, i + 0.5,
            f"#{r['id']}\n{r['from']}–{r['to']}",
            ha="center", va="center",
            color="white", fontsize=7, fontweight="bold",
        )

    # Mark remaining-gap spans in the reservation panel too (faint red)
    for g in remaining_gaps:
        ax_bot.axvspan(
            to_mdate(g["gap_start"]),
            to_mdate(g["gap_end"] + timedelta(days=1)),
            alpha=0.12, color="#cc4444",
        )

    ax_bot.set_ylim(0, max(n_res, 1))
    ax_bot.set_yticks([i + 0.5 for i in range(n_res)])
    ax_bot.set_yticklabels([f"#{r['id']}" for r in final_reservations], fontsize=8)
    ax_bot.set_xlabel("Date")

    # ── Shared x-axis formatting ──────────────────────────────────────────────
    ax_bot.set_xlim(to_mdate(TARGET_START), to_mdate(TARGET_END))
    ax_bot.xaxis.set_major_locator(mdates.WeekdayLocator(byweekday=mdates.MO))
    ax_bot.xaxis.set_major_formatter(mdates.DateFormatter("%b %-d"))
    plt.setp(ax_bot.get_xticklabels(), rotation=45, ha="right", fontsize=8)

    plt.tight_layout()
    plt.savefig(PLOT_PATH, dpi=150, bbox_inches="tight")
    log.info("Availability plot saved to %s", PLOT_PATH)
    if show:
        plt.show()
    plt.close(fig)


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Fill CERN hostel reservation gaps.")
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Parse and detect gaps but do NOT submit any form changes.",
    )
    parser.add_argument(
        "--no-headless", dest="headless", action="store_false",
        help="Show the browser window (useful for debugging login selectors).",
    )
    parser.set_defaults(headless=True)
    parser.add_argument(
        "--interval", type=int, default=CHECK_INTERVAL_MINUTES, metavar="MINUTES",
        help=f"Minutes between checks (default: {CHECK_INTERVAL_MINUTES}).",
    )
    parser.add_argument(
        "--plot", action="store_true",
        help="After each check, show a matplotlib timeline of reservations, gaps, and bookable dates.",
    )
    args = parser.parse_args()

    run(dry_run=args.dry_run, headless=args.headless, interval_minutes=args.interval,
        show_plot=args.plot)


if __name__ == "__main__":
    main()
