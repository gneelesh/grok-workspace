# AI Engineer Job Search (Daily)

Automated daily search workflow for **AI Engineer** roles — *AI Engineer, Forward Deployed AI Engineer, AI/Python Engineer, Applied AI Engineer, LLM/GenAI Engineer*.

Same engine as `.grok/skills/presales-job-search/SKILL.md`, pointed at a **separate track** via `ai-engineer-track.json`, so the two searches never touch each other's state or output.

## Files

| File | Purpose |
|---|---|
| `ai-engineer-jobs-2026.md` | **Output** — updated in place each run |
| `ai-engineer-state.json` | Tracks job URLs, first_seen, run history |
| `ai-engineer-inbox.json` | Agent writes today's search results here |
| `ai-engineer-track.json` | Track config — output paths, section headings |
| `claude-ai-engineer.md` | This file — the workflow |
| `.grok/skills/presales-job-search/scripts/job_search.py` | Shared merge / render / prune engine |
| `.grok/skills/presales-job-search/scripts/prune_closed.py` | Shared URL checker for closed listings |

**Every command in this workflow must export the track config first** — without it the script writes to the presales files:

```bash
export JOB_TRACK_CONFIG=ai-engineer-track.json
```

## Workflow (execute every time — do not skip steps)

### Step 0 — Initialize if needed

```bash
export JOB_TRACK_CONFIG=ai-engineer-track.json
python3 .grok/skills/presales-job-search/scripts/job_search.py status
```

First ever run: `total_jobs` is 0 and no state file exists — that is expected. Skip `bootstrap` (there is no prior markdown to import) and go straight to Step 1. The first `merge` detects the cold start, prints `starting a new track from scratch`, and creates both the state file and the output markdown.

### Step 0.5 — Prune closed listings (skip on first run)

```bash
python3 .grok/skills/presales-job-search/scripts/job_search.py prune
```

- Checks every URL in state (~2s delay between requests)
- Removes listings with "no longer accepting applications" or equivalent
- LinkedIn 429 / Monster 403 → kept (unverified, not removed)
- Note `removed_count` and company names for the user report

### Step 1 — Run web searches

Execute **all 5 search passes** below. Prefer LinkedIn's guest job API — it returns real job cards without login, unlike `web_search` which mostly returns aggregate listing pages:

```
https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords=<terms>&location=<loc>&f_TPR=r604800&start=0
```

Useful parameters: `f_WT=2` (remote only) · `f_E=1,2` (internship/entry) · `f_E=2,3` (entry/associate) · `f_TPR=r604800` (past week) · `start=25` for page 2.

| Pass | Keywords | Location |
|---|---|---|
| 1 — Core AI Engineer (remote) | `AI Engineer` | United States + `f_WT=2` |
| 2 — Forward Deployed | `Forward Deployed Engineer` / `Applied AI Engineer` | United States |
| 3 — AI + Python | `AI Python Engineer` / `LLM Engineer` / `GenAI Engineer` | United States |
| 4 — Hub cities | `AI Engineer` / `Machine Learning Engineer` | SF Bay Area · New York · Seattle · Austin · Boston · Denver |
| 5 — Monster | `ai engineer` / `machine learning engineer` | monster.com (expect 403 — fall back to `web_search`) |

Fetch enough postings to cover **at least 40–60 relevant roles**.

### Boolean strings (for LinkedIn UI alerts)

**Alert A — AI Engineer (Remote US)**
```
("AI Engineer" OR "Artificial Intelligence Engineer" OR "Applied AI Engineer" OR "GenAI Engineer")
AND (Python OR LLM OR "large language model" OR RAG OR agents)
NOT ("Staff" OR "Principal" OR "Director" OR "VP")
```

**Alert B — Forward Deployed AI Engineer**
```
("Forward Deployed Engineer" OR "Forward Deployed AI Engineer" OR "Forward Deployed Software Engineer"
 OR "Solutions Engineer, AI" OR "AI Field Engineer" OR "Deployment Engineer")
AND (AI OR LLM OR GenAI OR "machine learning")
```

**Alert C — AI / Python Engineer**
```
("AI Engineer" OR "Machine Learning Engineer" OR "ML Engineer" OR "Python Engineer" OR "Software Engineer, AI")
AND (Python AND (LLM OR PyTorch OR TensorFlow OR "generative AI" OR NLP OR RAG OR LangChain))
NOT ("Principal" OR "Staff" OR "Distinguished" OR "Research Scientist")
```

**Alert D — LLM / GenAI product engineering**
```
("LLM Engineer" OR "GenAI Engineer" OR "Generative AI Engineer" OR "AI Software Engineer" OR "Agent Engineer")
AND (OpenAI OR Anthropic OR Claude OR "fine-tuning" OR embeddings OR "vector database" OR evals)
```

**Alert E — ML platform / AI infrastructure**
```
("ML Platform Engineer" OR "AI Infrastructure Engineer" OR "MLOps Engineer" OR "Inference Engineer")
AND (Kubernetes OR GPU OR Ray OR Kubeflow OR "model serving" OR vLLM)
```

### Step 2 — Build inbox JSON

Write results to `ai-engineer-inbox.json` at workspace root.

```json
{
  "search_date": "2026-09-10",
  "jobs": [
    {
      "company": "Company Name",
      "description": "**Role title** (Location). 1-2 sentence summary — stack, seniority, why it fits.",
      "url": "https://www.linkedin.com/jobs/view/...",
      "link_text": "Apply on LinkedIn",
      "section": "apply_first"
    }
  ]
}
```

**Rules:**
- `url` is the unique key — full LinkedIn/Monster job view URL, deduplicate before writing
- Include jobs re-found from pruned state **plus** newly discovered jobs
- Do **not** re-add jobs removed in Step 0.5, or any posting showing "no longer accepting applications"

### Filtering rules

**Include:** AI Engineer · Applied AI Engineer · Forward Deployed (AI/Software) Engineer · AI/ML Engineer · LLM Engineer · GenAI Engineer · Machine Learning Engineer · Python Engineer with AI scope · AI Software Engineer · MLOps / ML Platform Engineer · Agent Engineer

**Exclude:** Senior · Sr. · Principal · Distinguished · Staff · Director · VP · Research Scientist (PhD-gated) · pure Data Analyst / Data Engineer with no AI scope · prompt-only "AI trainer" gig listings · aggregator spam (Jobright.ai, "Jobs AI", Client Reach AI and similar reposters)

Check the job **title**, not just the description body — a posting whose title contains "Senior" or "Sr." is excluded even if the body says things like "not senior-gated." "Lead" titles are not excluded by this rule.

**Section assignment:**

| Signal | section value |
|---|---|
| Entry/associate/new-grad, 0–3 YOE, strong all-round fit | `apply_first` |
| Forward deployed, field engineer, customer-facing AI delivery | `fde` |
| Python-first application engineering with AI scope | `ai_python` |
| LLM / GenAI / agents / RAG product engineering | `genai_llm` |
| MLOps, model serving, GPU/inference infra, ML platform | `ml_platform` |
| Remote-US posting with no specific hub | `remote` |
| SF, Bay Area, San Jose, Palo Alto | `hub_sf` |
| NYC, NJ, New York | `hub_nyc` |
| Seattle, Bellevue | `hub_seattle` |
| Austin, Dallas, Houston, Texas | `hub_austin` |
| Boston, Denver, other US metros | `hub_boston` |
| monster.com URL | `monster` |
| Lead-band or research-heavy (not Senior-titled — those are excluded) | `stretch` |

### Step 3 — Merge, prune again, regenerate markdown

```bash
export JOB_TRACK_CONFIG=ai-engineer-track.json
python3 .grok/skills/presales-job-search/scripts/job_search.py merge --prune-after
```

This adds new URLs with `first_seen = today` (marked 🆕), updates existing jobs' `last_seen`, prunes newly added dead links, regenerates `ai-engineer-jobs-2026.md` with a **"What's new"** section, and appends to the run history table.

### Step 4 — Report to user

Summarize: run date · count of **new** jobs (company + title + link) · count of **pruned** jobs · total tracked · path to updated file.

### Step 5 — Commit (if git repo)

```bash
git add ai-engineer-jobs-2026.md ai-engineer-state.json ai-engineer-inbox.json
git commit -m "Daily AI engineer job search YYYY-MM-DD: N new, M pruned"
```

## Highlighting rules

| Marker | Meaning |
|---|---|
| 🆕 in **What's new** section | First seen on latest run |
| 🆕 **Company** in tables | Same — new this run |
| No marker | Seen in a prior run |

## Pruning rules

| Signal | Action |
|---|---|
| "No longer accepting applications" | **Remove** from state |
| HTTP 404 / 410 | **Remove** |
| LinkedIn 429 rate limit | **Keep** (retry next run) |
| Monster 403 bot block | **Keep** (cannot verify) |
| Job open and accepting | **Keep** |

## Troubleshooting

| Issue | Fix |
|---|---|
| Wrote to the presales file | `JOB_TRACK_CONFIG` was not exported — re-export and re-run |
| `inbox not found` | Write `ai-engineer-inbox.json` before merge |
| `bootstrap` errors on first run | Expected — there is no prior markdown; skip it, `merge` cold-starts the track |
| LinkedIn guest API returns nothing | Drop `f_TPR`/`f_E` filters, or widen keywords |
| Monster 403 | Use `web_search` on monster.com; note "verify on Monster" in description |
| Prune takes long | Normal — ~2s per URL; use `--delay=1.5` to speed up (higher 429 risk) |

## Do NOT

- Create a new dated file each day — always update `ai-engineer-jobs-2026.md`
- Run any command without `JOB_TRACK_CONFIG` set — it will overwrite the presales track
- Manually delete jobs from state — use `job_search.py prune` instead
- Skip the merge script — manual markdown edits break state sync
- Add a job whose title contains "Senior" or "Sr." to the inbox — check the title, not just the body text, before writing each entry
