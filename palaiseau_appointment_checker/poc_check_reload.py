#!/usr/bin/env python3
"""
Palaiseau Appointment Checker — Proof of Concept
=================================================
Opens the prefecture slot page, lets you solve the CAPTCHA manually,
then investigates whether a reload / re-navigation re-fetches slot data
without triggering the puzzle again.

Run with:
    python poc_check_reload.py

The browser window will open.  Solve the puzzle, then press Enter here.
"""

import json
import time
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth

TARGET_URL = "https://www.rdv-prefecture.interieur.gouv.fr/rdvpref/reservation/demarche/2246/creneau/"

# Stealth instance — patches ~20 JS properties that expose automation
STEALTH = Stealth(navigator_platform_override="Linux x86_64")

# ── helpers ───────────────────────────────────────────────────────────────────

def _is_interesting(url: str) -> bool:
    """True for XHR/fetch calls that look like API or page data requests."""
    parsed = urlparse(url)
    path = parsed.path.lower()
    # Skip static assets
    skip_exts = (".js", ".css", ".png", ".jpg", ".svg", ".woff", ".ico", ".map")
    return not any(path.endswith(e) for e in skip_exts)


def _slot_count(page) -> int | None:
    """
    Try to count available slots in the current page DOM.
    Returns None if the selector isn't found (i.e. we're back on the puzzle).
    """
    # Common patterns on French rdv-préfecture sites:
    # - <div class="creneau"> or <li class="creneau"> for each slot
    # - A message like "Aucun créneau disponible" when fully booked
    # - A table or list of radio buttons for time choices
    selectors_to_try = [
        "[class*='creneau']",
        "[class*='slot']",
        "input[type='radio']",
        "button[class*='time']",
        "td[class*='available']",
    ]
    for sel in selectors_to_try:
        try:
            elements = page.query_selector_all(sel)
            if elements:
                return len(elements)
        except Exception:
            pass
    return None


def _page_summary(page) -> dict:
    url = page.url
    title = page.title()
    try:
        body_text = page.inner_text("body")[:800].replace("\n", " ")
    except Exception:
        body_text = "(could not read body)"
    slots = _slot_count(page)
    return {"url": url, "title": title, "body_snippet": body_text, "slot_elements": slots}


def _print_summary(label: str, info: dict):
    print(f"\n{'─'*60}")
    print(f"  {label}")
    print(f"{'─'*60}")
    print(f"  URL   : {info['url']}")
    print(f"  Title : {info['title']}")
    print(f"  Slots : {info['slot_elements']}")
    print(f"  Body  : {info['body_snippet'][:300]}")


# ── main ──────────────────────────────────────────────────────────────────────

def run():
    captured_requests: list[dict] = []

    with sync_playwright() as pw:
        # Use real Chrome (not bundled Chromium) — harder for sites to fingerprint.
        # slow_mo removed: timing patterns can be a bot signal too.
        browser = pw.chromium.launch(channel="chrome", headless=False)
        ctx = browser.new_context(
            viewport={"width": 1280, "height": 900},
            # Realistic Accept-Language header
            extra_http_headers={"Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7"},
        )
        page = ctx.new_page()
        STEALTH.apply_stealth_sync(page)

        # ── Intercept all requests so we can log API calls ────────────────────
        def on_request(req):
            if _is_interesting(req.url):
                captured_requests.append({
                    "method":        req.method,
                    "url":           req.url,
                    "resource_type": req.resource_type,
                })

        def on_response(resp):
            if _is_interesting(resp.url) and resp.request.resource_type in ("xhr", "fetch", "document"):
                entry = {
                    "status": resp.status,
                    "url":    resp.url,
                    "type":   resp.request.resource_type,
                }
                # Try to capture JSON bodies — ignore errors (binary, large, etc.)
                try:
                    if "json" in (resp.headers.get("content-type", "")):
                        entry["body"] = resp.json()
                except Exception:
                    pass
                print(f"  [NET] {resp.status} {resp.request.resource_type:<8} {resp.url}")
                # Store separately so we can inspect later
                if not hasattr(run, "_responses"):
                    run._responses = []
                run._responses.append(entry)

        page.on("request",  on_request)
        page.on("response", on_response)

        # ── 1. Navigate to the puzzle page ───────────────────────────────────
        print(f"\nNavigating to:\n  {TARGET_URL}\n")
        print("Network requests will be logged above as they happen.\n")
        page.goto(TARGET_URL, wait_until="domcontentloaded")
        time.sleep(1)

        before = _page_summary(page)
        _print_summary("BEFORE puzzle solve", before)

        # ── 2. Wait for user to solve the puzzle ─────────────────────────────
        print("\n" + "="*60)
        print("  Solve the CAPTCHA/puzzle in the browser window.")
        print("  Once you can see the appointment slots (or a 'no slots'")
        print("  message), press Enter here.")
        print("="*60)
        input("\n  [Press Enter when ready] ")

        # Short pause so any post-solve XHR calls can complete
        time.sleep(2)

        after_solve = _page_summary(page)
        _print_summary("AFTER puzzle solve", after_solve)

        # ── 3. Try page.reload() ─────────────────────────────────────────────
        print("\n" + "="*60)
        print("  Testing: page.reload()")
        print("="*60)
        captured_requests.clear()
        if hasattr(run, "_responses"):
            run._responses.clear()

        STEALTH.apply_stealth_sync(page)
        page.reload(wait_until="domcontentloaded")
        time.sleep(2)

        after_reload = _page_summary(page)
        _print_summary("AFTER reload()", after_reload)
        print(f"\n  Requests captured during reload: {len(captured_requests)}")

        # ── 4. Try navigating back to the same URL ────────────────────────────
        print("\n" + "="*60)
        print("  Testing: page.goto(same URL)")
        print("="*60)
        captured_requests.clear()
        if hasattr(run, "_responses"):
            run._responses.clear()

        STEALTH.apply_stealth_sync(page)
        page.goto(TARGET_URL, wait_until="domcontentloaded")
        time.sleep(2)

        after_goto = _page_summary(page)
        _print_summary("AFTER goto(same URL)", after_goto)
        print(f"\n  Requests captured during goto: {len(captured_requests)}")

        # ── 5. Print captured API responses ──────────────────────────────────
        responses = getattr(run, "_responses", [])
        if responses:
            print("\n" + "="*60)
            print("  Captured API/document responses:")
            print("="*60)
            for r in responses:
                body_str = ""
                if "body" in r:
                    body_str = f"\n      body: {json.dumps(r['body'])[:300]}"
                print(f"  {r['status']} {r['type']:<8} {r['url']}{body_str}")

        # ── 6. Summary ────────────────────────────────────────────────────────
        print("\n" + "="*60)
        print("  SUMMARY")
        print("="*60)
        results = {
            "before_solve":  before["slot_elements"],
            "after_solve":   after_solve["slot_elements"],
            "after_reload":  after_reload["slot_elements"],
            "after_goto":    after_goto["slot_elements"],
        }
        for label, val in results.items():
            status = "✓ slots found" if val else ("✗ no slot elements" if val == 0 else "? unknown")
            print(f"  {label:<20}  slot_elements={val}  {status}")

        reload_stays = after_reload["url"] == after_solve["url"]
        goto_stays   = after_goto["url"] == after_solve["url"]
        print(f"\n  reload() stays on slots page : {'YES' if reload_stays else 'NO — went to puzzle'}")
        print(f"  goto()   stays on slots page : {'YES' if goto_stays   else 'NO — went to puzzle'}")

        # Keep the browser open so you can inspect the page
        print("\n  Browser left open — close it or press Enter to exit.")
        input()
        browser.close()


if __name__ == "__main__":
    run()