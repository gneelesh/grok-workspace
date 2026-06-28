---
name: presales-job-search
description: >
  Run daily pre-sales job search for Aaditya Ghosalkar: search LinkedIn and Monster
  across US hubs and remote, merge results into aaditya-job-search-2026.md, and
  highlight new postings with 🆕. Use when the user runs /presales-job-search,
  asks for daily job search, update job listings, refresh job search, or run job
  search skill.
---

# Presales Job Search (Daily)

Automated daily search workflow for **Aaditya Ghosalkar** pre-sales roles. Updates the same file every run and highlights **new** postings.

## Files

| File | Purpose |
|---|---|
| `aaditya-job-search-2026.md` | **Output** — updated in place each run |
| `aaditya-job-search-state.json` | Tracks job URLs, first_seen, run history |
| `aaditya-job-search-inbox.json` | Agent writes today's search results here |
| `aaditya-job-search-queries.md` | Boolean strings and search config |
| `.grok/skills/presales-job-search/scripts/job_search.py` | Merge + render engine |
| `.grok/skills/presales-job-search/references/search-workflow.md` | Full agent search instructions |

## Workflow (execute every time — do not skip steps)

### Step 0 — Initialize if needed

```bash
cd C:\Users\neele\grok-workspace
python .grok/skills/presales-job-search/scripts/job_search.py status
```

If `total_jobs` is 0 or state file missing:

```bash
python .grok/skills/presales-job-search/scripts/job_search.py bootstrap
```

### Step 1 — Run web searches

Read `.grok/skills/presales-job-search/references/search-workflow.md` and `aaditya-job-search-queries.md`.

Execute **all 4 search passes**:
1. LinkedIn remote (Alerts 1–2)
2. Non-Big-3 vendors (Alert 3)
3. Hub cities (Alerts 5–6 + Chicago, Atlanta, Boston, Dallas)
4. Monster.com sales engineer / presales

Use `web_search` and `WebFetch` on LinkedIn/Monster job URLs. Fetch enough postings to cover **at least 40–60 relevant roles** (include re-found existing jobs + any new ones).

### Step 2 — Build inbox JSON

Write results to `aaditya-job-search-inbox.json` at workspace root.

**Required schema** — see `references/search-workflow.md`. Each job:

```json
{
  "company": "Company Name",
  "description": "Role title (Location). 1-2 sentence summary.",
  "url": "https://www.linkedin.com/jobs/view/...",
  "link_text": "Apply on LinkedIn",
  "section": "apply_first"
}
```

Include jobs from the previous state that are still active (re-found today) so `last_seen` updates correctly.

### Step 3 — Merge and regenerate markdown

```bash
python .grok/skills/presales-job-search/scripts/job_search.py merge
```

This:
- Adds **new URLs** with `first_seen = today` → marked 🆕 in markdown
- Updates existing jobs' `last_seen`
- Regenerates `aaditya-job-search-2026.md` with a **"What's new"** section at the top
- Appends row to **Run history** table

### Step 4 — Report to user

Summarize:
- Date of run
- Count of **new** jobs (list company + title + link)
- Total tracked jobs
- Path to updated file

Example:

> **Daily search complete (2026-06-29)**  
> 🆕 **3 new:** Bitwarden SE, Cync SE, IBM CSE  
> **62 total** tracked → `aaditya-job-search-2026.md`

### Step 5 — Commit (if git repo)

```bash
git add aaditya-job-search-2026.md aaditya-job-search-state.json aaditya-job-search-inbox.json
git commit -m "Daily presales job search YYYY-MM-DD: N new"
git push
```

Only commit if user has been pushing this repo; skip if user declines.

## Highlighting rules

| Marker | Meaning |
|---|---|
| 🆕 in **What's new** section | First seen on latest run |
| 🆕 **Company** in tables | Same — new this run |
| No marker | Seen in a prior run |

After the next day's run, yesterday's 🆕 markers disappear from tables (jobs remain listed, but are no longer "new").

## Troubleshooting

| Issue | Fix |
|---|---|
| `inbox not found` | Write `aaditya-job-search-inbox.json` before merge |
| Duplicate companies | OK — URL is the unique key |
| LinkedIn fetch fails | Use web_search snippets; still capture URL |
| Monster JS block | Use search result title + URL; note "verify on Monster" in description |

## Do NOT

- Create a new dated file each day — always update `aaditya-job-search-2026.md`
- Delete jobs from state unless user asks — keep historical listings
- Skip the merge script — manual markdown edits break state sync