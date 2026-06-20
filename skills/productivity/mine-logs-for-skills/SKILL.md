---
name: mine-logs-for-skills
description: Analyze your own AI coding-assistant session history (Claude Code AND OpenAI Codex) to discover recurring workflows and propose new skill candidates (global or project-scoped), plus surface usage insights. Use when the user wants to mine/analyze their logs/transcripts/history for skill ideas, find repeated tasks worth automating, or audit how they use their AI tools.
---

# Mining AI assistant logs for new skill candidates

Your transcripts are a record of every task you've actually done. This skill turns
that history into **proposed skills** and **usage insights** — using a cheap
deterministic distill step plus your own agentic reasoning (semantic
understanding, not regex clustering).

It reads **both** assistants' transcript stores:
- **Claude Code** — `~/.claude/projects/<dashed-cwd>/<uuid>.jsonl` (message-stream)
- **OpenAI Codex** — `~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl` (event-stream)

**Where does it look?** Both stores live at fixed home-relative paths, so the
skill does NOT need to detect which assistant is running it — it reads whichever
stores exist and **extracts from both by default** (`--source both`). A missing
store is silently skipped. `cwd` is the join key, so the same repo worked in
either tool groups together in the corpus. Narrow with `--source claude|codex`.

## Pipeline

### Step 1 — Distill (deterministic, cheap)

Run the distiller (path is relative to this skill's directory — the runtime tells
you the skill's base directory):

```bash
python3 scripts/distill.py                 # both sources (default)
python3 scripts/distill.py --source codex  # or claude / both
# options: --since YYYY-MM-DD, --max-prompt-chars N, --claude-dir, --codex-dir, --out
```

Outputs (default `~/.cache/mine-logs-for-skills/`):
- `corpus.md` — size-bounded digest: per-source counts, a **global tool-frequency
  table** (the single best at-a-glance signal of what you automate), and prompts
  grouped by project (each session tagged `[claude]`/`[codex]`). **Read this first.**
- `distilled.jsonl` — one complete record per session (source, project, prompts,
  tool_counts, tool_sequence, timestamps). Use Grep/Read for drill-down.

### Step 1b — Dashboard (optional, visual)

Render a self-contained HTML dashboard (KPI cards, top-tools chart, busiest
projects, per-source split, monthly activity) — aggregates only, no raw prompt
text, safe to share:

```bash
python3 scripts/dashboard.py    # reads distilled.jsonl → dashboard.html
```
Open the printed `dashboard.html` in a browser. No external dependencies (works
offline; embeds no remote scripts).

### Step 2 — Analyze (agentic: semantic reasoning, this is the point)

Read `corpus.md`, then reason over it the way only an LLM can. Do NOT just count
strings — recognize *intent* even when wording differs.

- **Cluster by intent**, not exact text. Collapse near-duplicates (e.g. the many
  auto-generated `/security-review` "Review this change…" prompts are ONE recurring
  workflow already covered by a command — note it, don't propose it).
- **Route global vs project**: count how many *distinct* project paths a cluster
  appears in. Many projects → **user-level** skill; one repo → **project-level**.
- **Cross-tool signal**: a workflow that shows up in BOTH Claude and Codex logs is
  a strong, tool-agnostic skill candidate.
- **For scale**, fan out subagents (Explore / general-purpose), one per project
  group or corpus slice, returning structured findings; then synthesize.
- **Cross-reference existing skills** so you don't propose a duplicate.

### Step 3 — Propose

Per candidate: **name**, one-line **description** (trigger sentence), **scope**
(global vs project + distinct-project count), **evidence** (2-4 real prompts),
**frequency**, **sketch** (SKILL.md + helper), and the **friction it removes**.
Also surface non-skill **insights**: heavily-used tools/MCPs, repeated failures,
multi-turn workflows that could be shortened.

### Step 4 — Author (on approval only)

For each approved candidate, use a skill-authoring flow to generate a properly
structured `SKILL.md` (+ helper) in the correct location. Validate any shipped
code before writing.

## Bonus: secret hygiene

`scripts/scan_secrets.py` scans both stores for plaintext tokens and reports
redacted locations (high-confidence prefixed tokens vs. low-confidence 40-hex that
also matches git SHAs). Useful before sharing/retaining logs.

## Guardrails

- Logs are personal and may contain secrets. Keep all analysis local; never send
  corpus contents to an external service.
- Don't auto-create skills — always show candidates and get explicit approval.
- Re-runnable: as history grows, re-run Step 1 with `--since` to analyze only new
  sessions.
