#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CERN SCEM Catalogue Scraper
===========================
Navigates the catalogue entirely by clicking links — no hardcoded section IDs.
Walks the tree recursively: group pages → subsection pages → item detail pages,
using the on-page "Group" breadcrumb to go back up after each node.

Configure TARGET_SECTION_CODES to choose which top-level sections to scrape.

Usage:
    python cern_gas_scraper.py

Open the Chromium window, log in when prompted, then press Enter in the terminal.

Output files (written to the current directory):
    cern_gases.csv   cern_gases.json   cern_gases.md   cern_gas_scraper.log
"""

import asyncio
import csv
import json
import logging
import re
import sys
import time
from collections import defaultdict
from pathlib import Path

from playwright.async_api import async_playwright
from playwright_stealth import Stealth

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

TARGET_SECTION_CODES = ["60", "61"]

BASE_URL    = "https://edh.cern.ch/edhcat/Browser"
ROOT_URL    = f"{BASE_URL}?command=changeTopNode&argument=1&top=1"
OUTPUT_CSV  = Path("cern_gases.csv")
OUTPUT_JSON = Path("cern_gases.json")
OUTPUT_MD   = Path("cern_gases.md")
LOG_FILE    = Path("cern_gas_scraper.log")
PAGE_TIMEOUT = 60_000   # ms

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def setup_logging():
    fmt = "%(asctime)s %(levelname)-8s %(message)s"
    logging.basicConfig(
        level=logging.DEBUG,
        format=fmt,
        handlers=[
            logging.FileHandler(LOG_FILE, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Navigation primitives
# All navigation is done by clicking real page elements so that the browser
# includes the session objid in the form submission and the server can serve
# pages from its warm cache.  page.goto() and page.evaluate() are avoided for
# within-catalogue navigation because they bypass this warm path and cause
# multi-minute hangs on certain sections.
# ---------------------------------------------------------------------------

def clean(text: str) -> str:
    return " ".join(text.split()).strip()


async def wait_for_catalogue(page):
    await page.wait_for_load_state("domcontentloaded")
    await page.wait_for_selector("form[name='MainForm']", timeout=PAGE_TIMEOUT)


async def click_link(page, element, label: str = ""):
    """Click an element and wait for the catalogue page to load."""
    t = time.monotonic()
    async with page.expect_navigation(wait_until="domcontentloaded", timeout=PAGE_TIMEOUT):
        await element.click()
    await page.wait_for_selector("form[name='MainForm']", timeout=PAGE_TIMEOUT)
    log.debug("  click '%s' → %.1fs", label, time.monotonic() - t)


async def go_up(page) -> bool:
    """
    Click the 'Group' breadcrumb to go up one level in the tree.
    Returns True on success.
    """
    link = await page.query_selector("a:has-text('Group')")
    if link:
        await click_link(page, link, "Group↑")
        return True
    log.warning("  No 'Group' breadcrumb found — cannot go up")
    return False


async def go_to_root(page):
    """Return to the catalogue root by clicking the Browse button."""
    btn = await page.query_selector("a[href*='doIndex']")
    if btn:
        await click_link(page, btn, "doIndex→root")
    else:
        log.warning("Browse button not found — cold goto root")
        await page.goto(ROOT_URL)
        await wait_for_catalogue(page)


async def find_and_click_section(page, section_code: str) -> str:
    """
    On the root page, find the changeTopNode link for `section_code` (e.g. "60"),
    click it, and return the section label.  Returns "" if not found.
    """
    rows = await page.query_selector_all("tr")
    for row in rows:
        scem_el = await row.query_selector("td.scem")
        if not scem_el:
            continue
        scem_text = clean(await scem_el.inner_text())
        if scem_text != section_code:
            continue
        label_el = await row.query_selector("td.tree")
        label = clean(await label_el.inner_text()) if label_el else section_code
        link = await row.query_selector("a[href*='changeTopNode']")
        if link:
            log.info("Clicking section %s — %s", section_code, label)
            await click_link(page, link, f"changeTopNode→{section_code}")
            return label
    log.warning("Section %s not found on root page", section_code)
    return ""

# ---------------------------------------------------------------------------
# Detail-page scraper
# ---------------------------------------------------------------------------

async def scrape_detail_page(page) -> dict:
    detail = {}
    SITE_TITLE = "cern stores catalogue"

    # Product title — skip the generic site header
    for selector in ("h1", "td.title", ".itemTitle", ".Title", "h2", "h3"):
        el = await page.query_selector(selector)
        if el:
            txt = clean(await el.inner_text())
            if txt and txt.lower() != SITE_TITLE:
                detail["detail_title"] = txt
                break

    # Description text below the title
    desc_parts = []
    for selector in ("p", "div.description", "td.description", "font"):
        for el in await page.query_selector_all(selector):
            txt = clean(await el.inner_text())
            if txt and len(txt) > 30 and txt.lower() != SITE_TITLE and txt not in desc_parts:
                desc_parts.append(txt)
        if desc_parts:
            break
    if desc_parts:
        detail["detail_description"] = "\n".join(desc_parts[:5])

    # Table label-value pairs — EDH uses rows of (label, value, label, value, …)
    for row in await page.query_selector_all("tr"):
        cells = await row.query_selector_all("td")
        if len(cells) < 2:
            continue
        for i in range(0, len(cells) - 1, 2):
            label = clean(await cells[i].inner_text()).rstrip(":")
            value = clean(await cells[i + 1].inner_text())
            if label and value and 2 < len(label) < 80 and not label.isdigit():
                detail[f"detail_{label}"] = value

    return detail

# ---------------------------------------------------------------------------
# Tree walker
# ---------------------------------------------------------------------------

async def scrape_item_list(page, section_code: str, section_label: str) -> list[dict]:
    """
    Scrape all items on a section page (one with table.itemList).
    For each item: click its link → scrape detail → click Group back.
    """
    item_rows = await page.query_selector_all("table.itemList tr")
    if len(item_rows) < 2:
        return []

    header_cells = await item_rows[0].query_selector_all("td, th")
    headers = [clean(await c.inner_text()) for c in header_cells]
    log.debug("    columns: %s", headers)

    # Snapshot row texts up-front (link handles go stale after navigation)
    snapshots: list[list[str]] = []
    for row in item_rows[1:]:
        cells = await row.query_selector_all("td")
        if cells and await row.query_selector("a[href*='showPage']"):
            snapshots.append([clean(await c.inner_text()) for c in cells])

    log.info("    %d items", len(snapshots))
    items: list[dict] = []

    for idx, row_texts in enumerate(snapshots):
        item_data = dict(zip(headers, row_texts))
        item_data["section_code"]  = section_code
        item_data["section_label"] = section_label
        scem = item_data.get("SCEM Code", f"item {idx + 1}")
        log.info("    [%d/%d] %s", idx + 1, len(snapshots), scem)

        try:
            # Re-query to get a non-stale link handle
            live_rows = await page.query_selector_all("table.itemList tr")
            data_rows = [r for r in live_rows[1:]
                         if await r.query_selector("a[href*='showPage']")]
            if idx >= len(data_rows):
                log.error("    row %d vanished — skipping", idx)
                items.append(item_data)
                continue

            link = await data_rows[idx].query_selector("a[href*='showPage']")
            await click_link(page, link, scem)

            detail = await scrape_detail_page(page)
            item_data.update(detail)

            if not await go_up(page):
                # Can't get back to the list — recover cold
                log.warning("    recovering to section list via browser back")
                await page.go_back()
                await wait_for_catalogue(page)

        except Exception as e:
            log.error("    error on %s: %s", scem, e)
            try:
                await page.go_back()
                await wait_for_catalogue(page)
            except Exception:
                pass

        items.append(item_data)

    return items


async def discover_children(page, parent_code: str) -> list[tuple[str, str]]:
    """
    Discover direct children of the current group page.

    The EDH page always shows a persistent sidebar tree that includes ALL
    sibling sections at every level.  Filtering by the parent SCEM prefix
    ("60." for section 60, "60.01." for section 60.01, etc.) keeps only
    entries that actually belong to this node and ignores all sidebar siblings.

    Returns [(scem_text, label), …] in page order.
    """
    children: list[tuple[str, str]] = []
    seen: set[str] = set()
    prefix = parent_code + "."
    NAV_FNS = ("showPage", "openNode", "changeTopNode")
    for row in await page.query_selector_all("tr"):
        scem_el = await row.query_selector("td.scem")
        if not scem_el:
            continue
        scem_text = clean(await scem_el.inner_text())
        if not scem_text or not scem_text.startswith(prefix) or scem_text in seen:
            continue
        link = await row.query_selector("a[href]")
        if not link:
            continue
        href = await link.get_attribute("href") or ""
        if not any(fn in href for fn in NAV_FNS):
            continue
        label_el = await row.query_selector("td.tree")
        label = clean(await label_el.inner_text()) if label_el else scem_text
        seen.add(scem_text)
        children.append((scem_text, label))
    return children


async def find_child_link(page, scem_text: str):
    """
    Re-find the navigation link for a child by its exact td.scem text.
    Link element handles go stale after navigation; re-querying by text is stable.
    """
    for row in await page.query_selector_all("tr"):
        scem_el = await row.query_selector("td.scem")
        if not scem_el:
            continue
        if clean(await scem_el.inner_text()) != scem_text:
            continue
        link = await row.query_selector("a[href]")
        if link:
            return link
    return None


async def scrape_node(page, node_code: str, node_label: str, depth: int = 0) -> list[dict]:
    """
    Recursively scrape the current page.

    • itemList table present  → leaf node, scrape items.
    • td.scem rows present    → group node, click each child link,
                                 recurse, then click Group breadcrumb back.

    All navigation is via real link clicks so the browser keeps the server
    session warm (avoids the multi-minute cold-load penalty).
    """
    indent = "  " * depth

    # --- Leaf: item-list page ---
    item_rows = await page.query_selector_all("table.itemList tr")
    if len(item_rows) > 1:
        log.info("%s[leaf] %s", indent, node_code)
        return await scrape_item_list(page, node_code, node_label)

    # --- Group: rows with td.scem + navigation link ---
    children = await discover_children(page, node_code)
    if not children:
        log.warning("%s[empty] %s — no items or children found", indent, node_code)
        return []

    log.info("%s[group] %s — %d children", indent, node_code, len(children))
    all_items: list[dict] = []

    for child_code, child_label in children:
        log.info("%s  → %s  (%s)", indent, child_code, child_label)
        try:
            target = await find_child_link(page, child_code)
            if target is None:
                log.warning("%s  link for '%s' not found on page", indent, child_code)
                continue

            await click_link(page, target, child_code)
            items = await scrape_node(page, child_code, child_label, depth + 1)
            all_items.extend(items)

            if not await go_up(page):
                log.warning("%s  can't go up from %s — stopping group", indent, child_code)
                break

        except Exception as e:
            log.error("%s  error in %s: %s", indent, child_code, e)

    return all_items

# ---------------------------------------------------------------------------
# Output writers
# ---------------------------------------------------------------------------

def write_csv(all_items: list[dict], path: Path):
    if not all_items:
        return
    priority = ["section_code", "section_label", "SCEM Code", "Unit", "Unit Price",
                "Stock", "Expected Delivery", "Direct Delivery",
                "Base gas", "Component 1 gas", "Component 2 gas", "Component 3 gas",
                "Pressure", "Capacity", "Delivered in", "Fitting", "Class",
                "Quality", "Impurities", "Lead time", "detail_title", "detail_description"]
    seen: set[str] = set()
    all_keys: list[str] = []
    for k in priority:
        if k not in seen:
            all_keys.append(k)
            seen.add(k)
    for item in all_items:
        for k in item:
            if k not in seen:
                all_keys.append(k)
                seen.add(k)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=all_keys, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(all_items)
    log.info("Wrote %d rows to %s", len(all_items), path)


def write_json(all_items: list[dict], path: Path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(all_items, f, indent=2, ensure_ascii=False)
    log.info("Wrote JSON to %s", path)


def write_markdown(all_items: list[dict], path: Path):
    lines = ["# CERN Experimental Gases\n", f"*{len(all_items)} items*\n"]
    by_section: dict[str, list[dict]] = defaultdict(list)
    for item in all_items:
        by_section[item.get("section_code", "unknown")].append(item)
    for section in sorted(by_section):
        items = by_section[section]
        label = items[0].get("section_label", "")
        lines.append(f"\n## {section} — {label}\n")
        lines.append("| SCEM Code | Description | Unit | Price (CHF) | Stock | Lead Time | Pressure | Capacity | Fitting |")
        lines.append("|-----------|-------------|------|-------------|-------|-----------|----------|----------|---------|")
        for item in items:
            scem     = item.get("SCEM Code", "")
            desc     = item.get("detail_title") or (item.get("Base gas", "") + " " + item.get("Component 1 gas", ""))
            unit     = item.get("Unit", "")
            price    = item.get("Unit Price", "")
            stock    = item.get("Stock", "")
            lead     = item.get("Lead time", item.get("Expected Delivery", ""))
            pressure = item.get("Pressure", "")
            capacity = item.get("Capacity", "")
            fitting  = item.get("Fitting", "")
            lines.append(f"| {scem} | {clean(desc)[:60]} | {unit} | {price} | {stock} | {lead} | {pressure} | {capacity} | {fitting} |")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    log.info("Wrote Markdown to %s", path)

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main():
    setup_logging()
    log.info("=" * 60)
    log.info("CERN Catalogue Scraper  (target sections: %s)", TARGET_SECTION_CODES)
    log.info("=" * 60)

    async with Stealth().use_async(async_playwright()) as p:
        browser = await p.chromium.launch(headless=False, slow_mo=100)
        context = await browser.new_context()
        page = await context.new_page()

        # Cold goto — unavoidable for the initial login page
        log.info("Opening catalogue: %s", ROOT_URL)
        await page.goto(ROOT_URL)

        print("\n" + "=" * 60)
        print("ACTION REQUIRED:")
        print("  Please log in to EDH in the browser window.")
        print("  Once the catalogue index is visible, press Enter here.")
        print("=" * 60)
        input("Press Enter when logged in and catalogue is visible > ")

        all_items: list[dict] = []

        for section_code in TARGET_SECTION_CODES:
            # Navigate to root so the section link is visible
            await go_to_root(page)

            label = await find_and_click_section(page, section_code)
            if not label:
                continue

            log.info("=== Scraping section %s — %s ===", section_code, label)
            items = await scrape_node(page, section_code, label)
            all_items.extend(items)
            log.info("Section %s done: %d items", section_code, len(items))

        await browser.close()

    log.info("Writing outputs — %d total items", len(all_items))
    write_csv(all_items, OUTPUT_CSV)
    write_json(all_items, OUTPUT_JSON)
    write_markdown(all_items, OUTPUT_MD)
    log.info("Done. Log: %s", LOG_FILE)


if __name__ == "__main__":
    asyncio.run(main())
