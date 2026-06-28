#!/usr/bin/env python3
"""
Presales job search state manager.
Bootstrap from markdown, merge new search results, regenerate aaditya-job-search-2026.md.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

WORKSPACE = Path(__file__).resolve().parents[4]
OUTPUT_MD = WORKSPACE / "aaditya-job-search-2026.md"
STATE_JSON = WORKSPACE / "aaditya-job-search-state.json"
JOBS_INBOX = WORKSPACE / "aaditya-job-search-inbox.json"

SECTION_ORDER = [
    ("apply_first", "## Apply first — best fit (~0–3 YOE)", None),
    ("channel_partners", "## Channel partners & non-Big-3 ecosystem", None),
    ("ai_genai", "## AI / GenAI / data platform (profile differentiator)", None),
    ("hub_nyc", "### New York / New Jersey", "hub"),
    ("hub_austin", "### Austin / Texas / Dallas", "hub"),
    ("hub_raleigh", "### Raleigh / Charlotte (Red Hat corridor)", "hub"),
    ("hub_sf", "### San Francisco Bay Area", "hub"),
    ("hub_chicago", "### Chicago", "hub"),
    ("hub_atlanta", "### Atlanta", "hub"),
    ("hub_boston", "### Boston / Denver / Seattle (remote-friendly)", "hub"),
    ("monster", "## Monster.com listings", None),
    ("stretch", "## Stretch roles (save for 12–24 months or apply if you meet bar)", None),
]

HEADER_TO_SECTION = {
    "## Apply first — best fit (~0–3 YOE)": "apply_first",
    "## Channel partners & non-Big-3 ecosystem": "channel_partners",
    "## AI / GenAI / data platform (profile differentiator)": "ai_genai",
    "## Hub city listings": "_hub_parent",
    "### New York / New Jersey": "hub_nyc",
    "### Austin / Texas / Dallas": "hub_austin",
    "### Raleigh / Charlotte (Red Hat corridor)": "hub_raleigh",
    "### San Francisco Bay Area": "hub_sf",
    "### Chicago": "hub_chicago",
    "### Atlanta": "hub_atlanta",
    "### Boston / Denver / Seattle (remote-friendly)": "hub_boston",
    "## Monster.com listings": "monster",
    "## Stretch roles (save for 12–24 months or apply if you meet bar)": "stretch",
}

TABLE_ROW_RE = re.compile(
    r"^\|\s*(?P<company>.+?)\s*\|\s*(?P<desc>.+?)\s*\|\s*\[(?P<link_text>[^\]]+)\]\((?P<url>[^)]+)\)\s*\|\s*$"
)


def normalize_url(url: str) -> str:
    return url.strip().rstrip("/")


def job_key(url: str) -> str:
    return normalize_url(url)


def today_str() -> str:
    return date.today().isoformat()


def load_state() -> dict[str, Any]:
    if STATE_JSON.exists():
        return json.loads(STATE_JSON.read_text(encoding="utf-8"))
    return {
        "last_run": None,
        "jobs": {},
        "run_history": [],
        "baseline_date": today_str(),
    }


def save_state(state: dict[str, Any]) -> None:
    STATE_JSON.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def parse_markdown_jobs(md_text: str) -> list[dict[str, str]]:
    jobs: list[dict[str, str]] = []
    current_section = "apply_first"

    for line in md_text.splitlines():
        header = line.strip()
        if header in HEADER_TO_SECTION:
            sec = HEADER_TO_SECTION[header]
            if sec != "_hub_parent":
                current_section = sec
            continue

        m = TABLE_ROW_RE.match(line.strip())
        if not m:
            continue

        company = m.group("company").strip()
        company = re.sub(r"^\*\*|\*\*$", "", company).strip()
        company = company.replace("🆕 ", "").strip()

        jobs.append(
            {
                "company": company,
                "description": m.group("desc").strip(),
                "link_text": m.group("link_text").strip(),
                "url": normalize_url(m.group("url")),
                "section": current_section,
            }
        )

    return jobs


def bootstrap_from_markdown() -> dict[str, Any]:
    if not OUTPUT_MD.exists():
        print(f"ERROR: {OUTPUT_MD} not found", file=sys.stderr)
        sys.exit(1)

    md_text = OUTPUT_MD.read_text(encoding="utf-8")
    parsed = parse_markdown_jobs(md_text)
    baseline = today_str()

    state = {
        "last_run": baseline,
        "baseline_date": baseline,
        "jobs": {},
        "run_history": [
            {
                "date": baseline,
                "action": "bootstrap",
                "total": len(parsed),
                "new_count": 0,
            }
        ],
    }

    for job in parsed:
        key = job_key(job["url"])
        state["jobs"][key] = {
            **job,
            "first_seen": baseline,
            "last_seen": baseline,
        }

    save_state(state)
    print(f"Bootstrapped {len(parsed)} jobs into {STATE_JSON}")
    return state


def merge_jobs(new_jobs: list[dict[str, str]], run_date: str | None = None) -> dict[str, Any]:
    run_date = run_date or today_str()
    state = load_state()

    if not state.get("jobs"):
        bootstrap_from_markdown()
        state = load_state()

    previous_run = state.get("last_run")
    new_count = 0
    updated_count = 0
    seen_keys: set[str] = set()

    for job in new_jobs:
        url = job.get("url") or job.get("link")
        if not url:
            continue
        key = job_key(url)
        seen_keys.add(key)

        company = job.get("company", "").strip()
        description = job.get("description", job.get("job_description", "")).strip()
        section = job.get("section", "apply_first")
        link_text = job.get("link_text", "Apply")

        if not company or not description:
            continue

        if key in state["jobs"]:
            existing = state["jobs"][key]
            existing["last_seen"] = run_date
            existing["company"] = company
            existing["description"] = description
            existing["section"] = section
            existing["link_text"] = link_text
            updated_count += 1
        else:
            state["jobs"][key] = {
                "company": company,
                "description": description,
                "link_text": link_text,
                "url": key,
                "section": section,
                "first_seen": run_date,
                "last_seen": run_date,
            }
            new_count += 1

    # Mark jobs not in this search pass (optional visibility)
    missing_count = 0
    for key, job in state["jobs"].items():
        if key not in seen_keys and job.get("last_seen") == previous_run:
            job["stale_since"] = run_date
            missing_count += 1

    state["last_run"] = run_date
    state.setdefault("run_history", []).append(
        {
            "date": run_date,
            "action": "merge",
            "new_count": new_count,
            "updated_count": updated_count,
            "searched_count": len(seen_keys),
            "not_in_latest_search": missing_count,
            "total": len(state["jobs"]),
        }
    )

    save_state(state)
    print(
        f"Merge complete: {new_count} new, {updated_count} updated, "
        f"{len(state['jobs'])} total in state"
    )
    return state


def is_new_job(job: dict[str, str], run_date: str) -> bool:
    return job.get("first_seen") == run_date


def format_company_cell(job: dict[str, str], run_date: str) -> str:
    company = job["company"]
    if is_new_job(job, run_date):
        return f"🆕 **{company}**"
    return f"**{company}**"


def render_markdown(state: dict[str, Any]) -> str:
    run_date = state.get("last_run") or today_str()
    jobs_by_section: dict[str, list[dict[str, str]]] = {s[0]: [] for s in SECTION_ORDER}

    for job in state["jobs"].values():
        sec = job.get("section", "apply_first")
        if sec not in jobs_by_section:
            sec = "apply_first"
        jobs_by_section[sec].append(job)

    for sec_jobs in jobs_by_section.values():
        sec_jobs.sort(key=lambda j: (0 if is_new_job(j, run_date) else 1, j["company"].lower()))

    new_jobs = [j for j in state["jobs"].values() if is_new_job(j, run_date)]
    new_jobs.sort(key=lambda j: j["company"].lower())

    last_history = state.get("run_history", [])
    prev_date = None
    if len(last_history) >= 2:
        prev_date = last_history[-2].get("date")

    lines: list[str] = [
        "# Aaditya Ghosalkar — Job Search Results (2026)",
        "",
        f"**Last updated:** {run_date}  ",
        f"**Previous run:** {prev_date or state.get('baseline_date', '—')}  ",
        f"**Total tracked:** {len(state['jobs'])}  ",
        f"**New this run:** {len(new_jobs)}  ",
        "",
        "**Profile:** ~2 YOE · UVA CS · AWS SAA + AI Practitioner · GenAI/POC delivery · Open to relocate US-wide  ",
        "**Search scope:** LinkedIn + Monster · US hubs + Remote  ",
        "**Roles:** Sales Engineer · Solutions Consultant · Presales · Associate SA  ",
        "",
        "> Jobs marked with 🆕 in the table were **first seen on the last search run**. Verify links before applying.",
        "",
        "---",
        "",
    ]

    if new_jobs:
        lines.extend(
            [
                f"## 🆕 What's new — {run_date}",
                "",
                f"**{len(new_jobs)} new posting(s)** since previous run ({prev_date or 'baseline'}).",
                "",
                "| company_name | job_description | link |",
                "|---|---|---|",
            ]
        )
        for job in new_jobs:
            lines.append(
                f"| {format_company_cell(job, run_date)} | {job['description']} | "
                f"[{job.get('link_text', 'Apply')}]({job['url']}) |"
            )
        lines.extend(["", "---", ""])
    else:
        lines.extend(
            [
                f"## 🆕 What's new — {run_date}",
                "",
                "No new postings since the previous run. All listings below are unchanged.",
                "",
                "---",
                "",
            ]
        )

    hub_started = False
    for section_id, heading, kind in SECTION_ORDER:
        section_jobs = jobs_by_section.get(section_id, [])
        if not section_jobs:
            continue

        if kind == "hub" and not hub_started:
            lines.extend(["## Hub city listings", ""])
            hub_started = True

        lines.extend([heading, ""])
        lines.extend(
            [
                "| company_name | job_description | link |",
                "|---|---|---|",
            ]
        )
        for job in section_jobs:
            lines.append(
                f"| {format_company_cell(job, run_date)} | {job['description']} | "
                f"[{job.get('link_text', 'Apply')}]({job['url']}) |"
            )
        lines.append("")

    lines.extend(
        [
            "---",
            "",
            "## Run history",
            "",
            "| date | new | updated | total |",
            "|---|---:|---:|---:|",
        ]
    )
    for entry in state.get("run_history", [])[-10:]:
        lines.append(
            f"| {entry.get('date', '—')} | {entry.get('new_count', '—')} | "
            f"{entry.get('updated_count', entry.get('updated', '—'))} | "
            f"{entry.get('total', '—')} |"
        )

    lines.extend(
        [
            "",
            "---",
            "",
            "*Auto-updated by `/presales-job-search` skill · "
            "State: `aaditya-job-search-state.json` · "
            "Queries: `aaditya-job-search-queries.md`*",
            "",
        ]
    )

    return "\n".join(lines)


def cmd_render() -> None:
    state = load_state()
    if not state.get("jobs"):
        state = bootstrap_from_markdown()
    content = render_markdown(state)
    OUTPUT_MD.write_text(content, encoding="utf-8")
    print(f"Rendered {OUTPUT_MD}")


def cmd_merge(path: Path | None) -> None:
    inbox = path or JOBS_INBOX
    if not inbox.exists():
        print(f"ERROR: inbox not found: {inbox}", file=sys.stderr)
        print("Agent should write search results to aaditya-job-search-inbox.json", file=sys.stderr)
        sys.exit(1)

    data = json.loads(inbox.read_text(encoding="utf-8"))
    jobs = data if isinstance(data, list) else data.get("jobs", [])
    state = merge_jobs(jobs)
    content = render_markdown(state)
    OUTPUT_MD.write_text(content, encoding="utf-8")
    print(f"Updated {OUTPUT_MD} with {len([j for j in state['jobs'].values() if is_new_job(j, state['last_run'])])} new job(s)")


def cmd_status() -> None:
    state = load_state()
    run_date = state.get("last_run", "never")
    total = len(state.get("jobs", {}))
    print(json.dumps({"last_run": run_date, "total_jobs": total, "state_file": str(STATE_JSON)}, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="Presales job search state tool")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("bootstrap", help="Import jobs from existing markdown into state")
    sub.add_parser("render", help="Regenerate markdown from state")
    sub.add_parser("status", help="Print state summary")

    merge_p = sub.add_parser("merge", help="Merge inbox JSON and regenerate markdown")
    merge_p.add_argument("--inbox", type=Path, default=None)

    args = parser.parse_args()

    if args.command == "bootstrap":
        bootstrap_from_markdown()
        cmd_render()
    elif args.command == "render":
        cmd_render()
    elif args.command == "merge":
        cmd_merge(args.inbox)
    elif args.command == "status":
        cmd_status()


if __name__ == "__main__":
    main()