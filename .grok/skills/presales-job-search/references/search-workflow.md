# Daily Search Workflow — Agent Reference

Read `aaditya-job-search-queries.md` in workspace root for Boolean strings.

## Daily sequence

1. **Prune** — `python .grok/skills/presales-job-search/scripts/job_search.py prune`
2. **Search** — all 4 passes below
3. **Inbox** — write `aaditya-job-search-inbox.json` (pruned state + new jobs)
4. **Merge + prune** — `python .grok/skills/presales-job-search/scripts/job_search.py merge --prune-after`

## Search passes (run all 4 each day)

### Pass 1 — LinkedIn remote (priority)

| Query | Location |
|---|---|
| Alert 1: Remote Cloud SE | United States · Remote |
| Alert 2: Remote AI / GenAI SE | United States · Remote |

### Pass 2 — Non-Big-3 vendors

| Query | Location |
|---|---|
| Alert 3: Oracle, IBM, Red Hat, Nutanix | United States |

### Pass 3 — Hub cities

| Query | Location |
|---|---|
| Alert 5 | Austin, TX + Raleigh, NC |
| Alert 6 | San Francisco Bay Area + New York, NY |
| Additional | Chicago, Atlanta, Boston, Dallas, Denver, Seattle |

### Pass 4 — Monster.com

Search: `sales engineer presales solutions engineer cloud` on [monster.com/jobs](https://www.monster.com/jobs/q-sales-engineer-jobs)

## Filtering rules

**Include:** Sales Engineer, Solutions Engineer, Presales, Solutions Consultant, Associate SA, Cloud Consultant, Client Engineering, Customer Success Engineer (technical), Technical Sales Specialist

**Exclude:** Principal, Distinguished, Staff, Director, VP, BDR, SDR, pure AE, IT Support Engineer

**Skip during search:** Postings showing "no longer accepting applications" — do not add to inbox.

**Section assignment:**

| Signal | section value |
|---|---|
| 0–3 YOE, entry-level, campus 2026 | `apply_first` |
| SHI, Arrow, CDW, WWT, Rackspace, partner | `channel_partners` |
| AI, GenAI, LLM, ML, data platform | `ai_genai` |
| NYC, NJ, New York | `hub_nyc` |
| Austin, Dallas, Houston, Texas | `hub_austin` |
| Raleigh, Charlotte, NC | `hub_raleigh` |
| SF, Bay Area, San Jose | `hub_sf` |
| Chicago | `hub_chicago` |
| Atlanta | `hub_atlanta` |
| Boston, Denver, Seattle | `hub_boston` |
| monster.com URL | `monster` |
| 5+ years required, senior only | `stretch` |

## Inbox JSON format

Write ALL active jobs found today to `aaditya-job-search-inbox.json`:

```json
{
  "search_date": "2026-06-28",
  "jobs": [
    {
      "company": "IBM",
      "description": "Customer Success Engineer — Entry Level 2026 (McLean, VA). Deliver POCs, demos, workshops.",
      "url": "https://www.linkedin.com/jobs/view/customer-success-engineer-entry-level-sales-program-2026-at-ibm-4427386901",
      "link_text": "Apply on LinkedIn",
      "section": "apply_first"
    }
  ]
}
```

**Rules:**
- `url` is the unique key — use full LinkedIn/Monster job view URL
- `description` = 1–3 sentences from posting (location, title, fit note)
- Deduplicate by URL before writing inbox
- Include jobs from **pruned state** (re-found today) AND new jobs
- Do **not** include jobs removed by prune or found closed during search

## After search

```bash
python .grok/skills/presales-job-search/scripts/job_search.py merge --prune-after
```

Prune-only (before search or standalone):

```bash
python .grok/skills/presales-job-search/scripts/job_search.py prune
python .grok/skills/presales-job-search/scripts/job_search.py prune --dry-run
```

Optional commit:

```bash
git add aaditya-job-search-2026.md aaditya-job-search-state.json aaditya-job-search-inbox.json
git commit -m "Daily presales job search $(date +%Y-%m-%d)"
git push
```