# skills

Agent skills for [SDLC with Agents](https://github.com/ramanshrivastava/sdlcwithagents) —
software engineering with AI agents. Each skill is a self-contained `SKILL.md`
(plus optional helper scripts) that works with [Claude Code](https://claude.com/claude-code)
and compatible agent runtimes.

## Layout

```
skills/
  <category>/
    <skill-name>/
      SKILL.md            # frontmatter (name, description) + instructions
      scripts/            # optional helper scripts
.claude-plugin/
  marketplace.json        # plugin manifest grouping skills by category
```

Categories follow the convention popularized by community skills repos
(`engineering/`, `productivity/`, `misc/`, …). Skills added over time.

## Skills

### productivity

| Skill | What it does |
|-------|--------------|
| [mine-logs-for-skills](./skills/productivity/mine-logs-for-skills/SKILL.md) | Mine your own Claude Code **and** OpenAI Codex transcripts to discover recurring workflows and propose new skill candidates, plus surface usage insights. |

## Install

**Single skill (manual):** copy a skill folder into your skills directory:

```bash
git clone https://github.com/ramanshrivastava/skills.git
cp -r skills/skills/productivity/mine-logs-for-skills ~/.claude/skills/
```

**Whole collection as a plugin marketplace:** point Claude Code at this repo's
`.claude-plugin/marketplace.json` (see the Claude Code plugin/marketplace docs),
then enable the `productivity` plugin.

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md) and the starter
[docs/skill-template.md](./docs/skill-template.md).

## License

[MIT](./LICENSE) © 2026 Raman Shrivastava
