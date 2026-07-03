---
name: presales-job-search
description: >
  Run daily pre-sales job search for Aaditya Ghosalkar: search LinkedIn and Monster
  across US hubs and remote, prune closed listings, merge results into
  aaditya-job-search-2026.md, and highlight new postings with 🆕. Use when the user
  runs /presales-job-search, asks for daily job search, update job listings, refresh
  job search, or run job search skill.
---

# Presales Job Search (Daily)

Automated daily search workflow for **Aaditya Ghosalkar** pre-sales roles. Each run **searches for new postings** and **removes closed / not-accepting listings**. Updates the same file every run and highlights **new** postings.

## Files

| File | Purpose |
|---|---|
| `aaditya-job-search-2026.md` | **Output** — updated in place each run |
| `aaditya-job-search-state.json` | Tracks job URLs, first_seen, run history |
| `aaditya-job-search-inbox.json` | Agent writes today's search results here |
| `aaditya-job-search-queries.md` | Boolean strings and search config |
| `.grok/skills/presales-job-search/scripts/job_search.py` | Merge, render, and prune commands |
| `.grok/skills/presales-job-search/scripts/prune_closed.py` | URL checker for closed listings |
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

### Step 0.5 — Prune closed listings (before search)

Remove jobs that are **no longer accepting applications** from the current state so they are not re-added to the inbox.

```bash
python .grok/skills/presales-job-search/scripts/job_search.py prune
```

- Checks every URL in state (~2s delay between requests; ~3–5 min for 90 jobs)
- Removes listings with "no longer accepting applications" or equivalent
- LinkedIn 429 / Monster 403 → kept (unverified, not removed)
- Note `removed_count` and company names for the user report

### Step 1 — Run web searches

Read `.grok/skills/presales-job-search/references/search-workflow.md` and `aaditya-job-search-queries.md`.

Execute **all 4 search passes**:
1. LinkedIn remote (Alerts 1–2)
2. Non-Big-3 vendors (Alert 3)
3. Hub cities (Alerts 5–6 + Chicago, Atlanta, Boston, Dallas)
4. Monster.com sales engineer / presales

Use `web_search` and `WebFetch` on LinkedIn/Monster job URLs. Fetch enough postings to cover **at least 40–60 relevant roles** (include re-found existing jobs from pruned state + any new ones).

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

**Rules:**
- Include all jobs from **pruned state** (re-found today) plus newly discovered jobs
- Do **not** re-add jobs removed in Step 0.5
- Skip URLs that show "no longer accepting applications" during search
- Deduplicate by URL before writing inbox

### Step 3 — Merge, prune again, regenerate markdown

```bash
python .grok/skills/presales-job-search/scripts/job_search.py merge --prune-after
```

This:
- Adds **new URLs** with `first_seen = today` → marked 🆕 in markdown
- Updates existing jobs' `last_seen`
- **Prunes closed listings** again (catches newly added dead links)
- Regenerates `aaditya-job-search-2026.md` with a **"What's new"** section at the top
- Appends rows to **Run history** table

Standalone prune (without merge) is also available:

```bash
python .grok/skills/presales-job-search/scripts/job_search.py prune --dry-run  # preview only
python .grok/skills/presales-job-search/scripts/job_search.py prune
```

### Step 4 — Report to user

Summarize:
- Date of run
- Count of **new** jobs (list company + title + link)
- Count of **pruned** jobs (list company names removed as closed)
- Total tracked jobs
- Path to updated file

Example:

> **Daily search complete (2026-07-03)**  
> 🆕 **5 new:** Dynatrace SE, Diagrid SE, Sigma SE, …  
> 🗑️ **3 pruned (closed):** Bitwarden, Descope, cplace  
> **90 total** tracked → `aaditya-job-search-2026.md`

### Step 5 — Commit (if git repo)

```bash
git add aaditya-job-search-2026.md aaditya-job-search-state.json aaditya-job-search-inbox.json
git commit -m "Daily presales job search YYYY-MM-DD: N new, M pruned"
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

## Pruning rules

| Signal | Action |
|---|---|
| "No longer accepting applications" | **Remove** from state |
| HTTP 404 / 410 | **Remove** |
| LinkedIn 429 rate limit | **Keep** (retry next run) |
| Monster 403 bot block | **Keep** (cannot verify) |
| Job open and accepting | **Keep** |

Prune runs **twice per daily workflow**: before search (Step 0.5) and after merge (`--prune-after`).

## Troubleshooting

| Issue | Fix |
|---|---|
| `inbox not found` | Write `aaditya-job-search-inbox.json` before merge |
| Duplicate companies | OK — URL is the unique key |
| LinkedIn fetch fails | Use web_search snippets; still capture URL |
| Monster JS block | Use search result title + URL; note "verify on Monster" in description |
| Prune takes long | Normal — ~2s per URL; use `--delay=1.5` to speed up (higher 429 risk) |
| False prune | Run `prune --dry-run` first; strict patterns avoid removing open jobs |

## Do NOT

- Create a new dated file each day — always update `aaditya-job-search-2026.md`
- Manually delete jobs from state — use `job_search.py prune` instead
- Skip the merge script — manual markdown edits break state sync
- Re-add jobs that prune removed as closed