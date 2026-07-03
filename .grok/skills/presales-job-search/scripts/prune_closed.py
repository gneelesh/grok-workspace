#!/usr/bin/env python3
"""Check job URLs and remove closed / not-accepting listings from state."""

from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

WORKSPACE = Path(__file__).resolve().parents[4]
STATE_JSON = WORKSPACE / "aaditya-job-search-state.json"
OUTPUT_MD = WORKSPACE / "aaditya-job-search-2026.md"

# Strict closed signals only — avoid false positives from LinkedIn chrome/footer text.
CLOSED_PATTERNS = [
    r"no longer accepting applications",
    r"not accepting applications",
    r"this job is no longer available",
    r"job is no longer available",
    r"closed-job__flavor",
    r"job posting has expired",
    r"this position has been filled",
    r"this job has been closed",
    r"posting is no longer active",
    r"couldn.?t find this job",
    r"the job you were looking for",
]
CLOSED_RE = re.compile("|".join(CLOSED_PATTERNS), re.IGNORECASE)

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def fetch_status(url: str, retries: int = 4) -> tuple[str, str, str]:
    """Return (url, status, reason). status: open|closed|unknown|error"""
    req = Request(url, headers={"User-Agent": USER_AGENT, "Accept-Language": "en-US,en;q=0.9"})
    last_reason = "unknown"

    for attempt in range(retries):
        try:
            with urlopen(req, timeout=25) as resp:
                code = resp.getcode()
                body = resp.read(900_000).decode("utf-8", errors="replace")
        except HTTPError as e:
            code = e.code
            body = e.read(300_000).decode("utf-8", errors="replace") if e.fp else ""
            if code in (404, 410):
                return url, "closed", f"HTTP {code}"
            if code == 429:
                last_reason = "HTTP 429 rate limited"
                time.sleep(3 * (attempt + 1))
                continue
            if CLOSED_RE.search(body):
                return url, "closed", f"HTTP {code} + closed text"
            return url, "unknown", f"HTTP {code}"
        except URLError as e:
            last_reason = str(e.reason)
            time.sleep(2)
            continue

        if code in (404, 410):
            return url, "closed", f"HTTP {code}"

        if CLOSED_RE.search(body):
            return url, "closed", "not accepting / no longer available"

        # Monster often blocks bots — keep unless explicit closed text
        if "monster.com" in url and code == 403:
            return url, "open", "Monster blocked bot (kept)"

        if "linkedin.com" in url:
            if re.search(r"public_jobs_topcard|job-details|description__text", body, re.I):
                return url, "open", "LinkedIn job page present"

        return url, "open", "ok"

    return url, "unknown", last_reason


def prune(dry_run: bool = False, delay_sec: float = 2.5) -> None:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from job_search import load_state, save_state, render_markdown

    state = load_state()
    jobs = state.get("jobs", {})
    urls = sorted(jobs.keys())
    print(f"Checking {len(urls)} job URLs (delay {delay_sec}s)...")

    closed_urls: list[str] = []
    unknown_urls: list[str] = []

    for i, url in enumerate(urls, 1):
        url, status, reason = fetch_status(url)
        company = jobs[url].get("company", "?")
        print(f"[{i}/{len(urls)}] {status.upper()}: {company} — {reason}")
        if status == "closed":
            closed_urls.append(url)
        elif status == "unknown":
            unknown_urls.append(url)
        time.sleep(delay_sec)

    print(f"\nClosed: {len(closed_urls)} | Unknown (kept): {len(unknown_urls)}")

    if dry_run:
        for u in closed_urls:
            print(f"  REMOVE: {jobs[u]['company']}: {u}")
        return

    for u in closed_urls:
        del state["jobs"][u]

    state.setdefault("run_history", []).append(
        {
            "date": state.get("last_run"),
            "action": "prune_closed",
            "removed_count": len(closed_urls),
            "unknown_kept": len(unknown_urls),
            "total": len(state["jobs"]),
        }
    )

    save_state(state)
    OUTPUT_MD.write_text(render_markdown(state), encoding="utf-8")
    print(f"Removed {len(closed_urls)} jobs. {len(state['jobs'])} remain.")
    print(f"Updated {OUTPUT_MD}")


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    delay = 2.5
    for arg in sys.argv[1:]:
        if arg.startswith("--delay="):
            delay = float(arg.split("=", 1)[1])
    prune(dry_run=dry, delay_sec=delay)