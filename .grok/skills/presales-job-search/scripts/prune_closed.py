#!/usr/bin/env python3
"""Check job URLs and remove closed / not-accepting listings from state."""

from __future__ import annotations

import re
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

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


def prune_closed_jobs(
    state: dict[str, Any],
    *,
    delay_sec: float = 2.0,
    dry_run: bool = False,
    verbose: bool = True,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """
    Remove closed / not-accepting listings from state.

    Returns (updated_state, stats) where stats contains:
      removed_count, unknown_kept, removed (list of {company, url, reason})
    """
    jobs = state.get("jobs", {})
    urls = sorted(jobs.keys())
    if verbose:
        print(f"Pruning closed listings: checking {len(urls)} URLs (delay {delay_sec}s)...")

    closed: list[tuple[str, str, str]] = []  # url, company, reason
    unknown_count = 0

    for i, url in enumerate(urls, 1):
        _, status, reason = fetch_status(url)
        company = jobs[url].get("company", "?")
        if verbose:
            print(f"  [{i}/{len(urls)}] {status.upper()}: {company} — {reason}")
        if status == "closed":
            closed.append((url, company, reason))
        elif status == "unknown":
            unknown_count += 1
        if delay_sec > 0:
            time.sleep(delay_sec)

    removed_records = [
        {"company": company, "url": url, "reason": reason} for url, company, reason in closed
    ]

    if not dry_run and closed:
        for url, _, _ in closed:
            del state["jobs"][url]
        state.setdefault("run_history", []).append(
            {
                "date": state.get("last_run"),
                "action": "prune_closed",
                "removed_count": len(closed),
                "unknown_kept": unknown_count,
                "total": len(state["jobs"]),
            }
        )

    stats = {
        "removed_count": len(closed),
        "unknown_kept": unknown_count,
        "removed": removed_records,
        "total_after": len(state["jobs"]) if not dry_run else len(jobs) - len(closed),
    }

    if verbose:
        print(
            f"Prune complete: {stats['removed_count']} removed, "
            f"{stats['unknown_kept']} unverified (kept), "
            f"{stats['total_after']} remain"
        )

    return state, stats


def main() -> None:
    import argparse
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from job_search import OUTPUT_MD, load_state, render_markdown, save_state

    parser = argparse.ArgumentParser(description="Prune closed job listings from state")
    parser.add_argument("--dry-run", action="store_true", help="Report only; do not modify state")
    parser.add_argument("--delay", type=float, default=2.0, help="Seconds between URL checks")
    args = parser.parse_args()

    state = load_state()
    state, stats = prune_closed_jobs(state, delay_sec=args.delay, dry_run=args.dry_run)

    if not args.dry_run and stats["removed_count"] > 0:
        save_state(state)
        OUTPUT_MD.write_text(render_markdown(state), encoding="utf-8")
        print(f"Updated {OUTPUT_MD}")
    elif not args.dry_run:
        print("No closed listings found — state unchanged")


if __name__ == "__main__":
    main()