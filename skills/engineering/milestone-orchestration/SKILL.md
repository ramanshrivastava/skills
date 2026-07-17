---
name: milestone-orchestration
description: Run a large, correctness-critical build (a port, rewrite, protocol/serializer, or migration) as a team of AI agents — a persistent coordinator that never writes bulk code dispatches one implementation agent per milestone, and every PR passes a merge gate whose adversarial half finds the bugs green tests miss. Use when the user wants to port or rewrite a big codebase, run a multi-milestone project with subagents, set up review gates for agent-authored PRs, or coordinate a fleet of coding agents against a reference implementation.
---

# Milestone-gated multi-agent orchestration

A method for pointing a *team* of agents at a build too large and too
correctness-sensitive for one context: a **persistent coordinator** that never
writes bulk code dispatches **one implementation agent per milestone**, and every
PR passes a **merge gate** whose adversarial half is designed to catch exactly the
bugs a green test suite cannot.

Worked example: [rho](https://github.com/ramanshrivastava/rho), a byte-for-byte
Rust port of a ~31k-LOC Python agent harness. Its merge gate caught a real,
shipping-blocking bug in *every* milestone that the green suite missed — see
[PRs #2–#6](https://github.com/ramanshrivastava/rho/pulls?q=is%3Apr) and
`docs/methodology.md` in that repo.

## When to use

- Porting or rewriting a large codebase into another language, or reimplementing
  a protocol / serializer / wire format against a reference.
- A multi-milestone project big enough that you'll dispatch subagents.
- You need review gates for agent-authored PRs that go beyond "CI is green."
- **Precondition:** a *correctness oracle* you can extract up front (a reference
  implementation, a conformance spec, a golden corpus). No oracle → this is
  overkill; just dispatch one agent and review its PR.

## The roles

- **Coordinator** (this session, an expensive frontier model): grills the design,
  writes the plan + milestone ladder, dispatches milestone agents, runs the merge
  gate, owns the task board and memory files, runs the babysit cron. **Writes no
  bulk implementation code** — its scarce resource is judgment.
- **Milestone agent** (a strong but cheaper model, one per milestone): works from
  a self-contained brief on its own branch, opens a PR, resolves review-bot
  comments itself, reports back.
- **Cluster subagent** (optional, only for ~6k+ LOC milestones): the milestone
  agent becomes a temporary coordinator and splits work into modules, each in an
  **isolated git worktree**, merged back by the milestone agent.

## Steps

### 1. Grill first — lock the design before any code

Interview the user adversarially until every decision-tree branch is resolved
(scope, interop guarantees, dependencies, testing oracle, done-conditions). Refuse
to start coding. Output a table of **locked decisions**. Record it in a memory
file so it survives across sessions. Use a grilling skill if you have one.

### 2. Extract the correctness oracle

Before porting behavior, extract **golden fixtures from the reference's own code**
(call the exact functions it uses in production — don't hand-write expected
output). Pin the reference revision. Adopt one policy, in writing:

> **If a golden test diffs, the code is wrong — never the fixture.**

Where possible add a **bidirectional crosscheck**: run identical inputs through
both implementations, normalize nondeterminism (ids, timestamps), and byte-diff.
This frees review to hunt only for what fixtures can't catch.

### 3. Write the milestone ladder

Decompose into dependency-ordered milestones, each ~one agent context, each with a
**mechanical** definition-of-done. Put them on a shared task board with
`blockedBy` dependencies. A milestone is done when its DoD is *mechanically true*,
not when an agent says so.

### 4. Dispatch one agent per milestone

Give each milestone agent a brief using the template below. Dispatch via the Agent
tool with a cheaper-model override; reserve the frontier model for the
coordinator. See [templates.md](templates.md) for the full brief template.

### 5. Run the merge gate on every PR (no exceptions)

See the checklist below. This is the expensive part and the valuable part.

### 6. Keep the fleet alive

Schedule an hourly **babysit cron** that reads the task board, pings in-flight
agents, and distinguishes an idle heartbeat from a real stall (dead agent /
rate-limit death) — nudging or re-dispatching. Because the cron runs independent
of any live session, it recovers from an agent dying on a rate limit with zero
work lost. Treat crossed messages as idempotent status; reconcile against the task
board and git/PR state, not message order.

### 7. Write the teaching journal

Each milestone writes a `dev-notes/phase-N.md`: what was built, which idiom
replaced which and why, and any reference behavior *later* milestones must
respect. This is how knowledge survives the disposable-agent model.

## The merge gate checklist

For every PR, before a rebase-merge:

- [ ] **Mechanical re-run, independently** by the coordinator — tests, lint,
      format, and the crosscheck. Not "CI is green on the PR"; re-execute.
- [ ] **Adversarial review by a fresh agent** briefed to find what the passing
      tests can't (see prompt below). Suspected divergences are **proven
      empirically** — run both implementations and diff.
- [ ] **All review-bot threads resolved** — each comment either *fixed* (reply
      with the fix commit SHA) or *rebutted with evidence* (e.g. a grep over the
      reference proving it doesn't do the thing either). Ground truth beats a
      plausible bot suggestion; bots are often right and sometimes wrong.
- [ ] **A fix round** folds confirmed findings back in.
- [ ] **Rebase-merge** to keep history linear.

## The adversarial-review prompt (reusable)

> You are reviewing a milestone PR whose test suite is **already green**. Assume
> the happy path works and the fixtures match — do not re-verify them. Find what
> the passing tests *cannot* show:
> - error and failure paths (persistence, network, subprocess failure);
> - resource lifecycles (drops, cancellations, fds, child processes, locks);
> - timing/concurrency (per-read vs total timeouts, stream abandonment,
>   re-entrancy);
> - fidelity to the reference on inputs the fixtures don't cover (tolerant
>   parsing, legacy shapes, null vs absent).
> When you suspect a divergence, **prove it**: run both implementations on the
> same input and diff. Report only what you can demonstrate.

The rho gate found, via this brief: a `null` value bricking a whole session file
(M1), a harness bricked when a consumer drops the event stream (M2), a total
timeout killing any slow LLM stream (M3), a subprocess hang on a backgrounded
child (M4a), silent data loss on a persist failure (M4b) — all with a green suite.

## Recipes

- **Milestone brief, adversarial-review brief, babysit-cron, and worktree-cluster
  recipes:** see [templates.md](templates.md).

## Guardrails

- The coordinator must not slide into writing bulk implementation code — if you're
  typing hundreds of lines, dispatch instead.
- Never merge with unresolved bot threads; a rate-limited/slow bot is not a
  waiver — re-check for late comments first.
- Don't skip the oracle. Without something objective to diff against, the
  adversarial review degrades into taste and the method's value collapses.
- Match the reference's *actual* behavior over a reviewer's plausible suggestion;
  where you deliberately diverge, record why in the journal.
- Keep briefs self-contained (scope, reference files, DoD, git workflow) — a
  milestone agent starts cold.
