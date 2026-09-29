#!/usr/bin/env python3
"""
Palaiseau API Probe — PoC
=========================
After you solve the CAPTCHA once in the browser, this script:
  1. Captures every XHR/fetch call the SPA makes, with full headers + bodies.
  2. Extracts all cookies from the browser session.
  3. Replays the most-promising "slot" endpoints directly via requests (no browser).
  4. Writes a full dump to  api_probe_dump.json  for offline analysis.

Run:
    python poc_api_probe.py

Workflow:
  - Browser opens automatically.
  - Solve the CAPTCHA/puzzle in the browser window.
  - Press Enter in the terminal.
  - The script navigates through both demarche URLs to collect all API calls.
  - It then tries direct requests with the captured cookies.
  - Results are printed and written to api_probe_dump.json.
"""

import json
import time
from pathlib import Path
from urllib.parse import urlparse

import requests
from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth

TARGET_URLS = [
    "https://www.rdv-prefecture.interieur.gouv.fr/rdvpref/reservation/demarche/2246/creneau/",
    "https://www.rdv-prefecture.interieur.gouv.fr/rdvpref/reservation/demarche/2282/creneau/",
]

BASE_ORIGIN = "https://www.rdv-prefecture.interieur.gouv.fr"
DUMP_PATH   = Path("api_probe_dump.json")
STEALTH     = Stealth(navigator_platform_override="Linux x86_64")

# ── Helpers ───────────────────────────────────────────────────────────────────

SKIP_EXTS = (".js", ".css", ".png", ".jpg", ".jpeg", ".svg",
             ".woff", ".woff2", ".ttf", ".ico", ".map", ".gif", ".webp")

def _is_data_request(url: str, resource_type: str) -> bool:
    """True for requests that could carry slot data (XHR/fetch + HTML navigation)."""
    if resource_type not in ("xhr", "fetch", "document"):
        return False
    path = urlparse(url).path.lower()
    return not any(path.endswith(e) for e in SKIP_EXTS)


def _headers_dict(headers) -> dict:
    """Convert Playwright Headers to a plain dict."""
    try:
        return dict(headers)
    except Exception:
        return {}


def _safe_json(response) -> object | None:
    try:
        ct = response.headers.get("content-type", "")
        if "json" in ct:
            return response.json()
    except Exception:
        pass
    return None


def _safe_text(response, max_bytes: int = 2000) -> str | None:
    try:
        ct = response.headers.get("content-type", "")
        if "html" in ct or "text" in ct:
            return response.text()[:max_bytes]
    except Exception:
        pass
    return None

# ── Network capture ───────────────────────────────────────────────────────────

class NetworkCapture:
    def __init__(self):
        self.requests: list[dict]  = []
        self.responses: list[dict] = []

    def on_request(self, req):
        if _is_data_request(req.url, req.resource_type):
            self.requests.append({
                "method":   req.method,
                "url":      req.url,
                "type":     req.resource_type,
                "headers":  _headers_dict(req.headers),
                "post_data": req.post_data,
            })

    def on_response(self, resp):
        if not _is_data_request(resp.url, resp.request.resource_type):
            return
        entry = {
            "status":  resp.status,
            "url":     resp.url,
            "type":    resp.request.resource_type,
            "method":  resp.request.method,
            "req_headers":  _headers_dict(resp.request.headers),
            "resp_headers": _headers_dict(resp.headers),
        }
        j = _safe_json(resp)
        if j is not None:
            entry["json_body"] = j
        t = _safe_text(resp)
        if t is not None:
            entry["text_snippet"] = t

        self.responses.append(entry)
        body_hint = ""
        if j:
            body_hint = f"  JSON keys: {list(j.keys()) if isinstance(j, dict) else '[list]'}"
        print(f"  [NET] {resp.status} {resp.request.resource_type:<6} {resp.url}{body_hint}")

    def attach(self, page):
        page.on("request",  self.on_request)
        page.on("response", self.on_response)

    def clear(self):
        self.requests.clear()
        self.responses.clear()


# ── Browser helpers ───────────────────────────────────────────────────────────

def _wait_for_slots_page(page, url: str):
    """Navigate to url and block until the browser lands on /creneau/."""
    print(f"\n  → Navigating to {url}")
    page.goto(url, wait_until="domcontentloaded")
    time.sleep(1)

    if "/creneau/" in page.url:
        print("    Already on slots page.")
        return

    print("    CAPTCHA page detected.")
    print("\n" + "="*60)
    print("  Solve the CAPTCHA in the browser window, then press Enter.")
    print("="*60)
    input("\n  [Press Enter after solving] ")

    # Poll until browser lands on /creneau/
    while "/creneau/" not in page.url:
        try:
            page.wait_for_url("**/creneau/**", timeout=30_000)
        except Exception:
            print("    Still waiting…")
    print("    CAPTCHA solved — on slots page.")


def _extract_cookies(ctx) -> dict:
    """Return all cookies as a name→value dict."""
    try:
        raw = ctx.cookies()
        return {c["name"]: c["value"] for c in raw}
    except Exception:
        return {}


def _extract_all_cookies_for_requests(ctx) -> list[dict]:
    """Return cookies in a format usable by requests.Session."""
    try:
        return ctx.cookies()
    except Exception:
        return []


# ── Direct-request probing ────────────────────────────────────────────────────

def _build_requests_session(browser_cookies: list[dict],
                            sample_req_headers: dict) -> requests.Session:
    s = requests.Session()

    # Copy cookies
    for c in browser_cookies:
        s.cookies.set(c["name"], c["value"], domain=c.get("domain", ""))

    # Copy realistic headers from a real browser request
    keep = ("accept", "accept-language", "referer", "user-agent",
            "x-requested-with", "authorization", "x-csrftoken", "x-xsrf-token")
    for k, v in sample_req_headers.items():
        if k.lower() in keep:
            s.headers[k] = v

    s.headers.setdefault("User-Agent",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
    return s


def _probe_url_directly(session: requests.Session, url: str,
                        method: str = "GET", post_data: str | None = None) -> dict:
    result = {"url": url, "method": method}
    try:
        if method.upper() == "POST" and post_data:
            r = session.post(url, data=post_data, timeout=15,
                             headers={"Content-Type": "application/x-www-form-urlencoded"})
        else:
            r = session.get(url, timeout=15)
        result["status"] = r.status_code
        result["redirect_url"] = r.url
        ct = r.headers.get("content-type", "")
        result["content_type"] = ct
        if "json" in ct:
            try:
                result["json"] = r.json()
            except Exception:
                result["text"] = r.text[:1000]
        elif "html" in ct:
            result["text"] = r.text[:500]
            result["has_no_slots"]   = "Aucun créneau disponible" in r.text
            result["has_slots"]      = "Choisissez votre créneau" in r.text
            result["hit_captcha"]    = "/cgu/" in r.url or "puzzle" in r.text.lower()
    except Exception as exc:
        result["error"] = str(exc)
    return result


# ── Main ──────────────────────────────────────────────────────────────────────

def run():
    cap = NetworkCapture()
    dump = {
        "browser_responses": [],
        "cookies": {},
        "direct_probe_results": [],
    }

    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel="chrome", headless=False)
        ctx = browser.new_context(
            viewport={"width": 1280, "height": 900},
            extra_http_headers={"Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7"},
        )
        page = ctx.new_page()
        STEALTH.apply_stealth_sync(page)
        cap.attach(page)

        # ── Step 1: Visit first URL, solve CAPTCHA ────────────────────────────
        _wait_for_slots_page(page, TARGET_URLS[0])
        time.sleep(2)   # let post-load XHR calls settle

        print("\n  Triggering a manual slot-check navigation…")
        # Some SPAs re-fetch on anchor navigation; click around to trigger API calls
        try:
            page.reload(wait_until="domcontentloaded")
            time.sleep(2)
        except Exception:
            pass

        # ── Step 2: Visit second URL (session should carry over) ──────────────
        if len(TARGET_URLS) > 1:
            print(f"\n  Navigating to second URL: {TARGET_URLS[1]}")
            page.goto(TARGET_URLS[1], wait_until="domcontentloaded")
            time.sleep(2)
            if "/cgu/" in page.url:
                print("  WARNING: second URL triggered CAPTCHA — session did NOT carry over.")
            else:
                print("  Second URL loaded without CAPTCHA.")

        # ── Step 3: Harvest cookies ───────────────────────────────────────────
        all_cookies = _extract_all_cookies_for_requests(ctx)
        cookie_dict = {c["name"]: c["value"] for c in all_cookies}
        dump["cookies"] = cookie_dict
        print(f"\n  Cookies captured: {list(cookie_dict.keys())}")

        # Record browser responses
        dump["browser_responses"] = cap.responses

        browser.close()

    # ── Step 4: Try direct HTTP requests (no browser) ────────────────────────
    print("\n" + "="*60)
    print("  Browser closed.  Probing APIs directly with requests…")
    print("="*60)

    # Pick the best sample request headers from what we saw
    sample_headers: dict = {}
    for resp in cap.responses:
        if resp.get("req_headers"):
            sample_headers = resp["req_headers"]
            break

    session = _build_requests_session(all_cookies, sample_headers)

    # 4a. Try the main slot URLs directly
    for url in TARGET_URLS:
        print(f"\n  Direct GET: {url}")
        result = _probe_url_directly(session, url)
        dump["direct_probe_results"].append(result)
        _report_probe(result)

    # 4b. Try any XHR/fetch URLs we captured during the browser session
    seen_urls = set(TARGET_URLS)
    xhr_urls  = [
        r for r in cap.responses
        if r["type"] in ("xhr", "fetch") and r["url"] not in seen_urls
    ]
    print(f"\n  Found {len(xhr_urls)} XHR/fetch API calls to probe.")

    for r in xhr_urls:
        url = r["url"]
        if url in seen_urls:
            continue
        seen_urls.add(url)
        method    = r.get("method", "GET")
        post_data = None
        # Find matching request for POST body
        for req in cap.requests:
            if req["url"] == url and req["method"] == method:
                post_data = req.get("post_data")
                break
        print(f"\n  Direct {method}: {url}")
        result = _probe_url_directly(session, url, method=method, post_data=post_data)
        dump["direct_probe_results"].append(result)
        _report_probe(result)

    # ── Step 5: Dump everything to JSON ──────────────────────────────────────
    DUMP_PATH.write_text(json.dumps(dump, indent=2, default=str), encoding="utf-8")
    print(f"\n  Full dump written to: {DUMP_PATH.resolve()}")

    # ── Step 6: Summary ───────────────────────────────────────────────────────
    print("\n" + "="*60)
    print("  SUMMARY")
    print("="*60)
    for r in dump["direct_probe_results"]:
        url_short = r["url"][-80:]
        st        = r.get("status", "ERR")
        captcha   = r.get("hit_captcha", False)
        slots     = r.get("has_slots", False)
        no_slots  = r.get("has_no_slots", False)
        verdict   = ("CAPTCHA" if captcha else
                     "SLOTS AVAILABLE" if slots else
                     "no slots" if no_slots else
                     "json/other")
        print(f"  {st}  {verdict:<20}  …{url_short}")

    print()
    direct_work = any(
        not r.get("hit_captcha") and r.get("status", 999) < 400
        for r in dump["direct_probe_results"]
        if r["url"] in TARGET_URLS
    )
    if direct_work:
        print("  ✓ Direct requests worked!  Captcha-free polling may be possible.")
        print("    Check api_probe_dump.json — find the session cookie name and replicate it.")
    else:
        print("  ✗ Direct requests hit CAPTCHA or failed.")
        print("    The site checks bot-detection at the HTTP layer, not just in-browser.")
        print("    Consider keeping the browser session alive longer instead.")


def _report_probe(r: dict):
    status  = r.get("status",   "ERROR")
    captcha = r.get("hit_captcha", False)
    slots   = r.get("has_slots",   False)
    no_s    = r.get("has_no_slots", False)
    err     = r.get("error")
    j       = r.get("json")
    if err:
        print(f"    ERROR: {err}")
        return
    print(f"    status={status}  captcha={captcha}  slots={slots}  no_slots={no_s}")
    if j:
        keys = list(j.keys()) if isinstance(j, dict) else f"[list len={len(j)}]"
        print(f"    JSON keys: {keys}")
        # Print interesting-looking fields
        if isinstance(j, dict):
            for k in j:
                if any(w in k.lower() for w in ("creneau", "slot", "dispo", "avail", "date", "count")):
                    print(f"      {k}: {j[k]}")


if __name__ == "__main__":
    run()