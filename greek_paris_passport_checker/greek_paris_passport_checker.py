#!/usr/bin/env python3
"""
Greek passport appointments, Paris: slot watcher
=================================================
Watches the Greek Embassy in Paris passport schedule (SuperSaaS,
PASSPORT_SERVICE_PARIS / APPOINTMENT) and emails you when a slot opens.

No account or browser is needed to check: the public schedule page embeds the
booked intervals for "BUREAU 1", and the page's own ajax call returns them for
"BUREAU 2". A free slot = an opening-hours slot on an open weekday, inside the
schedule's season, not on a closure day, and not booked. This reproduces the
page's own "Disponibilites" list (checked 2026-11-18 against a real browser).

BOOKING does need a SuperSaaS account on that schedule ("veuillez vous
identifier"), so whoever books should create one and stay logged in beforehand.

Usage:
    python3 greek_paris_passport_checker.py --once           # print free slots, exit
    python3 greek_paris_passport_checker.py                  # watch, email new slots
    python3 greek_paris_passport_checker.py --before 2026-12-24 --interval 2 --to someone@example.org

Only slots that START before --before trigger an email; every change is logged.
Alerts go to --to (repeatable), or by default to the Gmail account in the creds
file (it emails itself); --also-self adds it to --to. Standard library only.
"""

import argparse
import json
import logging
import random
import re
import smtplib
import subprocess
import sys
import time
import urllib.parse
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from email.mime.text import MIMEText
from pathlib import Path
from zoneinfo import ZoneInfo

BASE = "https://www.supersaas.com"
PAGE = BASE + "/schedule/PASSPORT_SERVICE_PARIS/APPOINTMENT"
BOOK_URL = "https://www.supersaas.fr/schedule/PASSPORT_SERVICE_PARIS/APPOINTMENT"
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36"
ZONE = ZoneInfo("Europe/Paris")

HERE = Path(__file__).resolve().parent
STATE_FILE = HERE / "state.json"
LOG_FILE = HERE / "greek_paris_passport_checker.log"
GMAIL_CRED_PATH = Path.home() / "Desktop/creds/gmail_cred.txt"  # line 1 user, line 2 app password
ALERT_SOUND = "/usr/share/sounds/freedesktop/stereo/complete.oga"

log = logging.getLogger("greek_paris")
ALSO_SELF = False
BLOCKED_BACKOFF_MIN = 10  # wait after HTTP 403/429


def http_get(url, opener, referer=None):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "fr-FR,fr;q=0.9"})
    if referer:
        req.add_header("Referer", referer)
        req.add_header("X-Requested-With", "XMLHttpRequest")
    with opener.open(req, timeout=30) as r:
        return r.read().decode("utf-8")


def js_value(html, name, pattern):
    m = re.search(r"\b" + name + r"\s*=\s*(" + pattern + ")", html)
    if not m:
        raise ValueError(f"page layout changed: {name} not found")
    return m.group(1)


def fetch_schedule():
    """Returns {bureau name: resource dict} where 'data' lists the booked intervals."""
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor())
    html = http_get(PAGE, opener)
    sp_id = js_value(html, "sp_id", r"\d+")
    token = js_value(html, "token", r"\d+")
    services = dict(re.findall(r'service\[\d+\]=\{data:\[0,"(\d+)","([^"]+)"', html))  # rp_id -> name
    if not services:
        raise ValueError("page layout changed: no services found")
    i = html.find("rcache = ")
    if i < 0:
        raise ValueError("page layout changed: rcache not found")
    rcache = json.loads(html[i + 9:html.find("\n", i)].strip().rstrip(";"))
    rps = {k: v for k, v in rcache.items() if isinstance(v, dict) and "data" in v}
    missing = [rp for rp in services if rp not in rps]
    if missing:  # other bureaus: same request the page makes when you click them
        now = datetime.now(ZONE).strftime("%Y-%m-%d %H:%M")
        q = urllib.parse.urlencode({"token": token, "res": "~".join(f"{rp}_{now}_580i_o" for rp in missing),
                                    "nn": "true"})
        extra = json.loads(http_get(f"{BASE}/ajax/service/{sp_id}?{q}", opener, referer=PAGE))
        rps.update(extra.get("res", {}))
    out = {}
    for rp, name in services.items():
        if "data" not in rps.get(rp, {}):
            raise ValueError(f"no booking data for {name} ({rp})")
        out[name] = rps[rp]
    return out


def free_slots(rp, now_local):
    """Free slot start times as naive Paris-local datetimes (SuperSaaS stores local time as fake UTC)."""
    epoch = datetime(1970, 1, 1)
    busy = {a for a, _b, _c in rp["data"]}
    exc = [(a, b) for a, b, _ in rp.get("exc", [])]
    lo, hi = rp["season"]
    starts = [int(x) for x in str(rp["start"]).split()]
    ot = rp["open_times"]  # [open Sun..Sat, close Sun..Sat], minutes after midnight
    length = 60  # both bureaus are 1:00 services
    out = []
    day = datetime(now_local.year, now_local.month, now_local.day)
    end = epoch + timedelta(seconds=hi)
    while day < end:
        base = int((day - epoch).total_seconds())
        wd = (day.weekday() + 1) % 7  # 0 = Sunday
        if base >= lo and (rp["bit_prefs"] >> wd) & 1 and not any(a <= base < b for a, b in exc):
            for m in starts:
                if ot[wd] <= m and m + length <= ot[wd + 7]:
                    t = base + m * 60
                    slot = epoch + timedelta(seconds=t)
                    if t not in busy and slot > now_local:
                        out.append(slot)
        day += timedelta(days=1)
    return out


def check():
    now_paris = datetime.now(ZONE).replace(tzinfo=None)
    return {name: [s.strftime("%Y-%m-%d %H:%M") for s in free_slots(rp, now_paris)]
            for name, rp in fetch_schedule().items()}


def fmt(slot):
    return datetime.strptime(slot, "%Y-%m-%d %H:%M").strftime("%a %d %b %Y %H:%M")


def gmail_creds():
    lines = GMAIL_CRED_PATH.read_text().splitlines()
    return lines[0].strip(), lines[1].strip()


def send_email(subject, body, recipients):
    if not GMAIL_CRED_PATH.exists():
        log.warning("no Gmail creds at %s, not emailing", GMAIL_CRED_PATH)
        return
    try:
        uname, pword = gmail_creds()
        recipients = list(recipients) or [uname]
        if ALSO_SELF and uname not in recipients:
            recipients.append(uname)
        msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"], msg["From"], msg["To"] = subject, uname, ", ".join(recipients)
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
            s.login(uname, pword)
            s.sendmail(uname, recipients, msg.as_string())
        log.info("emailed %d recipient(s): %s", len(recipients), subject)
    except Exception as e:
        log.error("email failed: %s", e)


def play_sound():
    try:
        subprocess.Popen(["paplay", ALERT_SOUND], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--once", action="store_true", help="print current free slots and exit")
    ap.add_argument("--before", default="2026-12-24", help="email only for slots starting before this date")
    ap.add_argument("--from", dest="from_", default="0000-00-00", help="email only for slots on or after this date")
    ap.add_argument("--interval", type=float, default=2.0, help="minutes between checks (default 2, +/-20%% jitter)")
    ap.add_argument("--to", action="append", default=[], help="extra/explicit recipient (repeatable)")
    ap.add_argument("--also-self", action="store_true", help="with --to, also email the creds' own account")
    ap.add_argument("--no-sound", action="store_true")
    ap.add_argument("--test-email", action="store_true", help="send one test alert and exit")
    args = ap.parse_args()
    global ALSO_SELF
    ALSO_SELF = args.also_self

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s",
                        handlers=[logging.StreamHandler(sys.stdout)] +
                                 ([] if args.once else [logging.FileHandler(LOG_FILE, encoding="utf-8")]))

    if args.once:
        for name, slots in check().items():
            print(f"{name}: {len(slots)} free")
            for s in slots:
                print("   ", fmt(s))
        return
    if args.test_email:
        send_email("[Greek passport Paris] test alert", f"Test from the slot checker.\n{BOOK_URL}\n", args.to)
        return

    cutoff, start = args.before + " 00:00", args.from_ + " 00:00"
    try:
        seen = json.loads(STATE_FILE.read_text())
    except Exception:
        seen = {}
    first, fails = not seen, 0
    fail_since, fail_mailed = None, False
    log.info("watching %s, alerting on new slots from %s to before %s, every ~%.1f min", PAGE, args.from_, args.before, args.interval)
    while True:
        try:
            cur = check()
            fails, new = 0, {}
            for name, slots in cur.items():
                old = set(seen.get(name, []))
                added = [s for s in slots if s not in old]
                gone = sorted(old - set(slots))
                if added or gone or first:
                    log.info("%s: %d free | +%s | -%s", name, len(slots), added, gone)
                # on the first run, alert on what's already open too
                hot = [s for s in (slots if first else added) if start <= s < cutoff]
                if hot:
                    new[name] = hot
            if new:
                lines = [f"{name}: " + ", ".join(fmt(s) for s in hot) for name, hot in new.items()]
                body = ("Greek passport appointment slot(s) open, Embassy of Greece in Paris:\n\n  "
                        + "\n  ".join(lines)
                        + f"\n\nBook (log in to SuperSaaS first): {BOOK_URL}\n"
                          f"Detected {datetime.now():%Y-%m-%d %H:%M:%S}. Cancellations go fast.\n")
                send_email("[Greek passport Paris] slot open: " + "; ".join(lines), body, args.to)
                if not args.no_sound:
                    play_sound()
            seen, first = cur, False
            STATE_FILE.write_text(json.dumps(seen, indent=1))
            fail_since, fail_mailed = None, False
        except Exception as e:
            fails += 1
            fail_since = fail_since or time.time()
            log.error("check failed (%d in a row): %s", fails, e)
            # failures go to the creds' own account only, never to --to recipients
            if not fail_mailed and time.time() - fail_since > 30 * 60:
                send_email("[Greek passport Paris] checker failing",
                           f"Checks failing for 30+ min ({fails} in a row). Last error:\n{e}\n", [])
                fail_mailed = True
            if isinstance(e, urllib.error.HTTPError) and e.code in (403, 429):
                time.sleep(BLOCKED_BACKOFF_MIN * 60)  # rate-limited: hammering keeps the block alive
                continue
        time.sleep(args.interval * 60 * random.uniform(0.8, 1.2))


if __name__ == "__main__":
    main()
