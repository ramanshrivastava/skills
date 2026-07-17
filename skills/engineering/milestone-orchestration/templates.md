# Templates & recipes

Concrete, copy-pasteable pieces for `milestone-orchestration`. All generic — swap
the bracketed placeholders for your project.

## Milestone brief template

Give this to each milestone agent (via the Agent tool, cheaper-model override). It
must be self-contained — the agent starts cold.

```md
# Milestone [Mn]: [one-line scope]

## Context
[1–2 sentences: what the whole project is, where this milestone sits, the
one invariant that matters most — e.g. "byte-for-byte parity with <reference>".]

## Scope (do exactly this, no more)
- [bullet the concrete deliverables]
- [what is explicitly OUT of scope / stubbed until a later milestone]

## Reference files (ground truth)
- [path in the reference impl] — [why it matters]
- [fixtures / spec sections this milestone is graded against]

## Definition of done (mechanical — must be literally true)
- [ ] [e.g. every wire fixture parses → re-serializes byte-identical]
- [ ] [ported tests X, Y pass]
- [ ] tests + lint + format green; CI green
- [ ] dev-notes/phase-[n].md written (idioms chosen + reference behavior later
      milestones must respect)

## Git workflow
- Branch: [mn-short-name] off main.
- Commit incrementally; open a PR titled "[Mn]: ...".
- Resolve every review-bot comment yourself: FIX (reply with the fix commit SHA)
  or REBUTT with evidence (a grep over the reference proving parity). Ground
  truth beats a plausible suggestion.
- Do NOT merge. Report back with the PR URL when the DoD is met and bot threads
  are resolved.
```

## Adversarial-review brief (dispatch a fresh agent)

```md
Review PR [url]. Its test suite is ALREADY GREEN — do not re-verify the happy
path or the fixtures. Find what the passing tests cannot show:
- error/failure paths (persistence, network, subprocess failure)
- resource lifecycles (drops, cancellations, file descriptors, child processes,
  locks)
- timing/concurrency (per-read vs total timeouts, stream abandonment,
  re-entrancy)
- fidelity to <reference> on inputs the fixtures don't cover (tolerant parsing,
  legacy shapes, null vs absent)

When you suspect a divergence from <reference>, PROVE it: run both
implementations on the same input and diff the bytes/behavior. Report only what
you can demonstrate, most severe first, each with a concrete repro.
```

## Babysit cron recipe

Schedule a check on a fixed cadence (e.g. hourly) that runs **independent of any
live session** — that independence is what lets it recover from an agent dying on
a rate limit.

Each firing:

1. Read the shared task board: which milestones are `in_progress`, `blocked`,
   `done`.
2. For each in-flight milestone agent, check liveness (last message / commit /
   PR activity) and message it if quiet.
3. Distinguish an **idle heartbeat** (agent working, just quiet) from a **real
   stall** (agent dead, blocked, or rate-limit-killed on spawn).
4. On a stall: nudge, or re-dispatch the milestone from its brief. Reconcile
   against git/PR state, not message order — coordinator and agents message
   asynchronously, so "still working?" and "done, PR up" routinely cross.
5. Advance any milestone whose `blockedBy` dependencies are now `done`.

Sketch (pseudo):

```text
every 1h:
  board = read_task_board()
  for m in board.in_progress:
      if agent_dead(m) or rate_limited(m):
          redispatch(m.brief)          # zero work lost: PR/branch survive
      elif quiet(m) and not idle_heartbeat(m):
          nudge(m.agent)
  for m in board.pending:
      if all(dep.done for dep in m.blockedBy):
          dispatch(m.brief)
```

## Worktree cluster recipe (for ~6k+ LOC milestones)

When one milestone won't fit a single context, the milestone agent decomposes it
into **independent module clusters** and runs each in its own git worktree.

```bash
# Branch clusters off the MILESTONE branch, not main, so each cluster sees the
# scaffolding, shared interfaces, and config the milestone agent already
# committed. (Commit that shared groundwork before cutting clusters.)
git worktree add -b <milestone>-clusterA ../wt-clusterA <milestone>
git worktree add -b <milestone>-clusterB ../wt-clusterB <milestone>
# dispatch one subagent per worktree (Agent tool, worktree isolation)
# ... each works, commits, and reports back ...

# milestone agent merges the branches back onto the milestone branch and runs
# the milestone DoD on the union
git switch <milestone>
git merge <milestone>-clusterA <milestone>-clusterB
git worktree remove ../wt-clusterA && git worktree remove ../wt-clusterB
```

Rule for a clean split: **no shared mutable files between clusters.** Natural
module/package/crate boundaries (especially where the build graph forbids
cross-edges) make this safe; if two clusters must edit the same file, they aren't
independent — re-cut the split.

## Underlying primitives

The pattern maps onto generic agent-team primitives:

- **Agent spawn with a model override** — cheap models for milestones, the
  frontier model reserved for the coordinator; optional git-worktree isolation for
  parallel clusters.
- **A message mailbox with idle notifications** — asynchronous coordinator↔agent
  comms that wake on replies.
- **A shared task board with `blockedBy` dependencies** — encodes the milestone
  ladder so the coordinator and its cron see what's in-flight, done, or blocked.
- **Scheduled crons** — run the babysit check on a cadence, independent of any
  live session (hence rate-limit-death recovery).
- **Memory files** — small `name`/`description`/`type`-fronted notes indexed by a
  top-level `MEMORY.md`, persisting locked decisions and hard-won facts across
  sessions.
- **Custom agent definitions** — markdown files with `name`/`description`/`tools`/
  `model` frontmatter giving recurring roles (reviewer, researcher, test-writer) a
  fixed brief you dispatch by name.
