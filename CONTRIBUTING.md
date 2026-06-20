# Contributing a skill

1. **Pick a category** under `skills/` (`engineering/`, `productivity/`, `misc/`, …)
   and create `skills/<category>/<skill-name>/SKILL.md`. Use lowercase-kebab names.

2. **Write the SKILL.md** — start from [docs/skill-template.md](./docs/skill-template.md).
   Required frontmatter:
   ```yaml
   ---
   name: my-skill            # must match the directory name
   description: One sentence on WHAT it does and WHEN to invoke it — include the
                phrases a user would actually say, so the model auto-selects it.
   ---
   ```

3. **Bundle helpers** (optional) under `<skill-name>/scripts/`. Keep them generic:
   - no hardcoded personal paths (use `Path.home()` / flags),
   - no secrets or private data,
   - write generated output to a cache/temp dir, never into the skill folder.

4. **Register it** in [`.claude-plugin/marketplace.json`](./.claude-plugin/marketplace.json)
   (add the path to the right category plugin's `skills` array) and link it from
   the top-level `README.md` table and the category `README.md`.

5. **Verify** before opening a PR:
   - any scripts `python3 -m py_compile` cleanly and run;
   - `marketplace.json` is valid JSON;
   - no generated artifacts, secrets, or `__pycache__` are staged (`git status`).

## Principles

- A good `description` is the real trigger surface — phrase it the way a user
  would ask, not as a clean canonical name.
- Prefer deterministic helper scripts for the mechanical parts and let the agent
  do the judgment; don't hardcode what the model can reason about.
