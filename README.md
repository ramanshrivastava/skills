<div align="center">

# ⌘ RAMAN SKILLS

**Agent skills for software engineering with AI agents.**

Small, composable, model-agnostic — built from real shipped work, not vibe-coding.
Part of [SDLC with Agents](https://github.com/ramanshrivastava/sdlcwithagents).

[![License: MIT](https://img.shields.io/badge/License-MIT-cba6f7?style=flat-square)](./LICENSE)
[![Claude Code](https://img.shields.io/badge/Claude%20Code-plugin%20marketplace-94e2d5?style=flat-square)](https://code.claude.com)
[![Codex](https://img.shields.io/badge/OpenAI-Codex-fab387?style=flat-square)](https://openai.com/codex)
[![Skills](https://img.shields.io/badge/skills-2-89b4fa?style=flat-square)](#-skills)

</div>

---

These are [Agent Skills](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview):
self-contained folders — a `SKILL.md` plus optional helper scripts — that an agent loads
on demand. They’re portable (same format across Claude Code, Codex, and compatible runtimes),
composable (stack together), and efficient (loaded only when relevant).

This repo collects the ones worth sharing. More added over time.

## ▸ Install (30 seconds)

In **Claude Code**, add this repo as a plugin marketplace, then install a plugin:

```text
/plugin marketplace add ramanshrivastava/skills
/plugin install productivity@ramanshrivastava/skills
```

Prefer to grab a single skill by hand? Copy its folder into your skills directory:

```bash
git clone https://github.com/ramanshrivastava/skills.git
cp -r skills/skills/productivity/mine-logs-for-skills ~/.claude/skills/
```

## ▸ Skills

### engineering

| Skill | What it does |
|-------|--------------|
| [**milestone-orchestration**](./skills/engineering/milestone-orchestration/SKILL.md) | Run a large, correctness-critical build (port, rewrite, serializer, migration) as a **team of agents** — a coordinator that never writes bulk code dispatches one agent per milestone, and every PR passes a **merge gate** whose adversarial half finds the bugs green tests miss. |

### productivity

| Skill | What it does |
|-------|--------------|
| [**mine-logs-for-skills**](./skills/productivity/mine-logs-for-skills/SKILL.md) | Mine your own **Claude Code + OpenAI Codex** transcripts to discover recurring workflows, propose new skills, and render a usage dashboard. |

## ◆ Featured — mine-logs-for-skills

> **Your coding-agent logs are a goldmine.**

Every session you run is a record of what you actually do. This skill reads **both** your
Claude Code (`~/.claude/projects`) and OpenAI Codex (`~/.codex/sessions`) transcripts, distills
them deterministically into a compact corpus, then lets the agent reason over it to:

- ▸ **Propose new skills** — recurring workflows become candidate `SKILL.md`s (global vs. project-scoped, with evidence).
- ▸ **Surface insights** — most-used tools, repeated friction, multi-turn flows worth shortening.
- ▸ **Render a dashboard** — a self-contained, offline HTML view (KPIs, top tools, busiest projects, activity) in a Catppuccin Mocha theme — aggregates only, no raw prompt text.

```bash
python3 scripts/distill.py            # both sources by default → corpus.md + distilled.jsonl
python3 scripts/dashboard.py          # → dashboard.html
```

`cwd` is the join key, so the same repo worked in either assistant groups together — a true
cross-tool view. A `scan_secrets.py` helper flags plaintext tokens before you share logs.

## ▸ Layout

```text
skills/<category>/<skill>/SKILL.md     # frontmatter (name, description) + instructions
                         /scripts/     # optional helpers
.claude-plugin/marketplace.json        # plugin manifest grouping skills by category
```

## ▸ Philosophy

- **Deterministic where it’s mechanical, agentic where it’s judgment.** Helper scripts do the
  cheap, exact work (parsing, scanning, rendering); the model does the reasoning.
- **Local and private by default.** Skills that touch your logs keep everything on your machine
  and never emit raw prompt text into shareable artifacts.
- **A good `description` is the real interface** — phrased the way you’d actually ask, so the
  right skill auto-selects.

## ▸ Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md) and the starter [docs/skill-template.md](./docs/skill-template.md).

## ▸ License

[MIT](./LICENSE) © 2026 Raman Shrivastava
